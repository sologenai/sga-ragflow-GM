"""
GraphRAG SDK - Production-grade SDK for RAGFlow Knowledge Graph functionality

This SDK provides a comprehensive interface for interacting with RAGFlow's GraphRAG features,
including knowledge graph construction, node search, file associations, and content download.

Features:
- Knowledge graph construction and management
- Node search and filtering
- Associated file retrieval
- Content download in multiple formats
- Caching and performance optimization
- Error handling and retry mechanisms
- Authentication and authorization
- Rate limiting and throttling
- Comprehensive logging and monitoring

Author: RAGFlow Team
Version: 1.0.0
License: Apache 2.0
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Union, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import redis
from datetime import datetime, timedelta
import hashlib
import pickle
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GraphRAGError(Exception):
    """Base exception for GraphRAG SDK"""
    pass


class AuthenticationError(GraphRAGError):
    """Authentication related errors"""
    pass


class RateLimitError(GraphRAGError):
    """Rate limiting errors"""
    pass


class ValidationError(GraphRAGError):
    """Input validation errors"""
    pass


class NetworkError(GraphRAGError):
    """Network related errors"""
    pass


class EntityType(Enum):
    """Supported entity types in knowledge graph"""
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
    CONCEPT = "CONCEPT"
    PRODUCT = "PRODUCT"
    TECHNOLOGY = "TECHNOLOGY"
    OTHER = "OTHER"


class DownloadFormat(Enum):
    """Supported download formats"""
    TXT = "txt"
    JSON = "json"
    CSV = "csv"
    XLSX = "xlsx"


@dataclass
class GraphNode:
    """Knowledge graph node representation"""
    id: str
    entity_type: str
    description: Optional[str] = None
    pagerank: Optional[float] = None
    communities: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class GraphEdge:
    """Knowledge graph edge representation"""
    source: str
    target: str
    relation: str
    weight: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AssociatedFile:
    """Associated file representation"""
    id: str
    name: str
    type: str
    size: Optional[int] = None
    chunk_num: Optional[int] = None
    create_time: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TextChunk:
    """Text chunk representation"""
    id: str
    content: str
    docnm_kwd: str
    page_num_int: Optional[List[int]] = None
    important_kwd: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SearchResult:
    """Search result representation"""
    nodes: List[GraphNode]
    total_count: int
    page: int
    page_size: int
    has_more: bool


@dataclass
class AssociatedFilesResult:
    """Associated files result representation"""
    files: List[AssociatedFile]
    chunks: List[TextChunk]
    total_files: int
    total_chunks: int


class CacheManager:
    """Redis-based cache manager for SDK"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", ttl: int = 3600):
        self.redis_client = redis.from_url(redis_url)
        self.ttl = ttl
    
    def _generate_key(self, prefix: str, *args) -> str:
        """Generate cache key from arguments"""
        key_data = f"{prefix}:{':'.join(str(arg) for arg in args)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            data = self.redis_client.get(key)
            if data:
                return pickle.loads(data)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            ttl = ttl or self.ttl
            data = pickle.dumps(value)
            return self.redis_client.setex(key, ttl, data)
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return False


class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
    
    def is_allowed(self) -> bool:
        """Check if request is allowed"""
        now = time.time()
        # Remove old requests outside the window
        self.requests = [req_time for req_time in self.requests if now - req_time < self.window_seconds]
        
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False
    
    def wait_time(self) -> float:
        """Get wait time until next request is allowed"""
        if not self.requests:
            return 0
        oldest_request = min(self.requests)
        return max(0, self.window_seconds - (time.time() - oldest_request))


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for retrying failed operations"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (NetworkError, aiohttp.ClientError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (backoff ** attempt)
                        logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed")
                        break
                except Exception as e:
                    # Don't retry on non-network errors
                    logger.error(f"Non-retryable error: {e}")
                    raise
            
            raise last_exception or GraphRAGError("Operation failed after retries")
        return wrapper
    return decorator


class GraphRAGSDK:
    """
    Production-grade SDK for RAGFlow GraphRAG functionality
    
    This SDK provides a comprehensive interface for:
    - Knowledge graph construction and management
    - Node search and filtering
    - Associated file retrieval
    - Content download in multiple formats
    - Caching and performance optimization
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: str,
        cache_manager: Optional[CacheManager] = None,
        rate_limiter: Optional[RateLimiter] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize GraphRAG SDK
        
        Args:
            base_url: Base URL of RAGFlow API
            api_key: API key for authentication
            cache_manager: Optional cache manager for performance optimization
            rate_limiter: Optional rate limiter for API calls
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.cache_manager = cache_manager or CacheManager()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Session for connection pooling
        self.session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"GraphRAG SDK initialized with base_url: {self.base_url}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure aiohttp session is created"""
        if not self.session or self.session.closed:
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'GraphRAG-SDK/1.0.0'
                }
            )
    
    async def close(self):
        """Close the SDK and cleanup resources"""
        if self.session and not self.session.closed:
            await self.session.close()
        logger.info("GraphRAG SDK closed")
    
    def _validate_kb_id(self, kb_id: str) -> None:
        """Validate knowledge base ID"""
        if not kb_id or not isinstance(kb_id, str):
            raise ValidationError("Knowledge base ID must be a non-empty string")
    
    def _validate_node_id(self, node_id: str) -> None:
        """Validate node ID"""
        if not node_id or not isinstance(node_id, str):
            raise ValidationError("Node ID must be a non-empty string")
    
    async def _check_rate_limit(self):
        """Check rate limit before making request"""
        if not self.rate_limiter.is_allowed():
            wait_time = self.rate_limiter.wait_time()
            raise RateLimitError(f"Rate limit exceeded. Wait {wait_time:.2f} seconds")
    
    @retry_on_failure(max_retries=3)
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with error handling and retries"""
        await self._check_rate_limit()
        await self._ensure_session()
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.request(
                method=method,
                url=url,
                json=data,
                params=params
            ) as response:
                
                if response.status == 401:
                    raise AuthenticationError("Invalid API key or unauthorized access")
                elif response.status == 429:
                    raise RateLimitError("Rate limit exceeded")
                elif response.status >= 400:
                    error_text = await response.text()
                    raise NetworkError(f"HTTP {response.status}: {error_text}")
                
                result = await response.json()
                
                if not result.get('retcode') == 0:
                    error_msg = result.get('retmsg', 'Unknown error')
                    raise GraphRAGError(f"API error: {error_msg}")
                
                return result.get('data', {})
                
        except aiohttp.ClientError as e:
            raise NetworkError(f"Network error: {e}")
        except json.JSONDecodeError as e:
            raise GraphRAGError(f"Invalid JSON response: {e}")

    async def get_knowledge_graph(
        self,
        kb_id: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get knowledge graph for a knowledge base

        Args:
            kb_id: Knowledge base ID
            use_cache: Whether to use cache for this request

        Returns:
            Knowledge graph data with nodes and edges
        """
        self._validate_kb_id(kb_id)

        # Check cache first
        if use_cache:
            cache_key = self.cache_manager._generate_key("graph", kb_id)
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for knowledge graph: {kb_id}")
                return cached_result

        logger.info(f"Fetching knowledge graph for kb_id: {kb_id}")

        endpoint = f"/kb/{kb_id}/knowledge_graph"
        result = await self._make_request("GET", endpoint)

        # Cache the result
        if use_cache and result:
            cache_key = self.cache_manager._generate_key("graph", kb_id)
            await self.cache_manager.set(cache_key, result, ttl=1800)  # 30 minutes

        return result

    async def search_nodes(
        self,
        kb_id: str,
        query: str = "",
        entity_types: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20,
        use_cache: bool = True
    ) -> SearchResult:
        """
        Search nodes in knowledge graph

        Args:
            kb_id: Knowledge base ID
            query: Search query string
            entity_types: List of entity types to filter by
            page: Page number (1-based)
            page_size: Number of results per page
            use_cache: Whether to use cache for this request

        Returns:
            SearchResult with nodes and pagination info
        """
        self._validate_kb_id(kb_id)

        if page < 1:
            raise ValidationError("Page number must be >= 1")
        if page_size < 1 or page_size > 100:
            raise ValidationError("Page size must be between 1 and 100")

        # Check cache first
        if use_cache:
            cache_key = self.cache_manager._generate_key(
                "search", kb_id, query, str(entity_types), page, page_size
            )
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for node search: {kb_id}")
                return SearchResult(**cached_result)

        logger.info(f"Searching nodes in kb_id: {kb_id}, query: {query}")

        endpoint = f"/kb/{kb_id}/knowledge_graph/search"
        data = {
            "query": query,
            "entity_types": entity_types or [],
            "page": page,
            "page_size": page_size
        }

        result = await self._make_request("POST", endpoint, data=data)

        # Convert to SearchResult
        nodes = [GraphNode(**node) for node in result.get('nodes', [])]
        search_result = SearchResult(
            nodes=nodes,
            total_count=result.get('total_count', 0),
            page=page,
            page_size=page_size,
            has_more=result.get('has_more', False)
        )

        # Cache the result
        if use_cache:
            cache_key = self.cache_manager._generate_key(
                "search", kb_id, query, str(entity_types), page, page_size
            )
            await self.cache_manager.set(cache_key, asdict(search_result), ttl=600)  # 10 minutes

        return search_result

    async def get_node_associated_files(
        self,
        kb_id: str,
        node_id: str,
        use_cache: bool = True
    ) -> AssociatedFilesResult:
        """
        Get files and chunks associated with a node

        Args:
            kb_id: Knowledge base ID
            node_id: Node ID
            use_cache: Whether to use cache for this request

        Returns:
            AssociatedFilesResult with files and chunks
        """
        self._validate_kb_id(kb_id)
        self._validate_node_id(node_id)

        # Check cache first
        if use_cache:
            cache_key = self.cache_manager._generate_key("files", kb_id, node_id)
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for associated files: {kb_id}/{node_id}")
                return AssociatedFilesResult(**cached_result)

        logger.info(f"Getting associated files for node: {kb_id}/{node_id}")

        endpoint = f"/kb/{kb_id}/knowledge_graph/node/{node_id}/files"
        result = await self._make_request("GET", endpoint)

        # Convert to AssociatedFilesResult
        files = [AssociatedFile(**file) for file in result.get('files', [])]
        chunks = [TextChunk(**chunk) for chunk in result.get('chunks', [])]

        associated_files = AssociatedFilesResult(
            files=files,
            chunks=chunks,
            total_files=result.get('total_files', 0),
            total_chunks=result.get('total_chunks', 0)
        )

        # Cache the result
        if use_cache:
            cache_key = self.cache_manager._generate_key("files", kb_id, node_id)
            await self.cache_manager.set(cache_key, asdict(associated_files), ttl=900)  # 15 minutes

        return associated_files

    async def download_node_content(
        self,
        kb_id: str,
        node_id: str,
        format: DownloadFormat = DownloadFormat.TXT,
        include_metadata: bool = True,
        content_type: str = "chunks"
    ) -> bytes:
        """
        Download node content in specified format

        Args:
            kb_id: Knowledge base ID
            node_id: Node ID
            format: Download format (txt, json, csv, xlsx)
            include_metadata: Whether to include metadata
            content_type: Type of content to download (chunks, files, all)

        Returns:
            Downloaded content as bytes
        """
        self._validate_kb_id(kb_id)
        self._validate_node_id(node_id)

        logger.info(f"Downloading content for node: {kb_id}/{node_id}, format: {format.value}")

        endpoint = f"/kb/{kb_id}/knowledge_graph/node/{node_id}/download"
        data = {
            "type": content_type,
            "format": format.value,
            "include_metadata": include_metadata
        }

        # For download, we need to handle binary response
        await self._check_rate_limit()
        await self._ensure_session()

        url = f"{self.base_url}{endpoint}"

        try:
            async with self.session.post(url, json=data) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid API key or unauthorized access")
                elif response.status == 429:
                    raise RateLimitError("Rate limit exceeded")
                elif response.status >= 400:
                    error_text = await response.text()
                    raise NetworkError(f"HTTP {response.status}: {error_text}")

                content = await response.read()
                return content

        except aiohttp.ClientError as e:
            raise NetworkError(f"Network error during download: {e}")

    async def get_graph_statistics(
        self,
        kb_id: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get knowledge graph statistics

        Args:
            kb_id: Knowledge base ID
            use_cache: Whether to use cache for this request

        Returns:
            Graph statistics including node count, edge count, etc.
        """
        self._validate_kb_id(kb_id)

        # Check cache first
        if use_cache:
            cache_key = self.cache_manager._generate_key("stats", kb_id)
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for graph statistics: {kb_id}")
                return cached_result

        logger.info(f"Getting graph statistics for kb_id: {kb_id}")

        endpoint = f"/kb/{kb_id}/knowledge_graph/statistics"
        result = await self._make_request("GET", endpoint)

        # Cache the result
        if use_cache and result:
            cache_key = self.cache_manager._generate_key("stats", kb_id)
            await self.cache_manager.set(cache_key, result, ttl=3600)  # 1 hour

        return result
