"""
GraphRAG SDK Factory

This module provides factory methods and convenience functions for creating
and configuring GraphRAG SDK instances.

Author: RAGFlow Team
Version: 1.0.0
"""

import logging
from typing import Optional, Dict, Any
from .graphrag_sdk import GraphRAGSDK, CacheManager, RateLimiter
from .config import GraphRAGConfig, ConfigManager, setup_logging

logger = logging.getLogger(__name__)


class GraphRAGSDKFactory:
    """Factory for creating GraphRAG SDK instances"""
    
    @classmethod
    def create_from_config(cls, config: GraphRAGConfig) -> GraphRAGSDK:
        """
        Create SDK instance from configuration
        
        Args:
            config: GraphRAG configuration
            
        Returns:
            Configured GraphRAG SDK instance
        """
        # Setup logging
        setup_logging(config.logging)
        
        # Create cache manager
        cache_manager = None
        if config.cache.enabled:
            cache_manager = CacheManager(
                redis_url=config.cache.redis_url,
                ttl=config.cache.default_ttl
            )
        
        # Create rate limiter
        rate_limiter = None
        if config.rate_limit.enabled:
            rate_limiter = RateLimiter(
                max_requests=config.rate_limit.max_requests,
                window_seconds=config.rate_limit.window_seconds
            )
        
        # Create SDK instance
        sdk = GraphRAGSDK(
            base_url=config.base_url,
            api_key=config.api_key,
            cache_manager=cache_manager,
            rate_limiter=rate_limiter,
            timeout=config.security.timeout,
            max_retries=config.retry.max_retries
        )
        
        logger.info("GraphRAG SDK instance created successfully")
        return sdk
    
    @classmethod
    def create_from_env(cls) -> GraphRAGSDK:
        """
        Create SDK instance from environment variables
        
        Returns:
            Configured GraphRAG SDK instance
        """
        config = ConfigManager.from_env()
        return cls.create_from_config(config)
    
    @classmethod
    def create_from_file(cls, config_path: str) -> GraphRAGSDK:
        """
        Create SDK instance from configuration file
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configured GraphRAG SDK instance
        """
        config = ConfigManager.from_file(config_path)
        return cls.create_from_config(config)
    
    @classmethod
    def create_auto(cls) -> GraphRAGSDK:
        """
        Auto-discover configuration and create SDK instance
        
        Returns:
            Configured GraphRAG SDK instance
        """
        config = ConfigManager.auto_discover()
        return cls.create_from_config(config)
    
    @classmethod
    def create_simple(
        cls,
        base_url: str,
        api_key: str,
        enable_cache: bool = True,
        enable_rate_limit: bool = True
    ) -> GraphRAGSDK:
        """
        Create SDK instance with simple configuration
        
        Args:
            base_url: Base URL of RAGFlow API
            api_key: API key for authentication
            enable_cache: Whether to enable caching
            enable_rate_limit: Whether to enable rate limiting
            
        Returns:
            Configured GraphRAG SDK instance
        """
        # Create cache manager
        cache_manager = CacheManager() if enable_cache else None
        
        # Create rate limiter
        rate_limiter = RateLimiter() if enable_rate_limit else None
        
        # Create SDK instance
        sdk = GraphRAGSDK(
            base_url=base_url,
            api_key=api_key,
            cache_manager=cache_manager,
            rate_limiter=rate_limiter
        )
        
        logger.info("Simple GraphRAG SDK instance created")
        return sdk


# Convenience functions for common operations
async def search_knowledge_graph(
    base_url: str,
    api_key: str,
    kb_id: str,
    query: str = "",
    entity_types: Optional[list] = None,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    Convenience function to search knowledge graph
    
    Args:
        base_url: Base URL of RAGFlow API
        api_key: API key for authentication
        kb_id: Knowledge base ID
        query: Search query string
        entity_types: List of entity types to filter by
        page: Page number (1-based)
        page_size: Number of results per page
        
    Returns:
        Search results
    """
    sdk = GraphRAGSDKFactory.create_simple(base_url, api_key)
    
    async with sdk:
        result = await sdk.search_nodes(
            kb_id=kb_id,
            query=query,
            entity_types=entity_types,
            page=page,
            page_size=page_size
        )
        return {
            'nodes': [node.__dict__ for node in result.nodes],
            'total_count': result.total_count,
            'page': result.page,
            'page_size': result.page_size,
            'has_more': result.has_more
        }


async def get_node_files(
    base_url: str,
    api_key: str,
    kb_id: str,
    node_id: str
) -> Dict[str, Any]:
    """
    Convenience function to get node associated files
    
    Args:
        base_url: Base URL of RAGFlow API
        api_key: API key for authentication
        kb_id: Knowledge base ID
        node_id: Node ID
        
    Returns:
        Associated files and chunks
    """
    sdk = GraphRAGSDKFactory.create_simple(base_url, api_key)
    
    async with sdk:
        result = await sdk.get_node_associated_files(kb_id=kb_id, node_id=node_id)
        return {
            'files': [file.__dict__ for file in result.files],
            'chunks': [chunk.__dict__ for chunk in result.chunks],
            'total_files': result.total_files,
            'total_chunks': result.total_chunks
        }


async def download_node_data(
    base_url: str,
    api_key: str,
    kb_id: str,
    node_id: str,
    format: str = "txt",
    include_metadata: bool = True
) -> bytes:
    """
    Convenience function to download node content
    
    Args:
        base_url: Base URL of RAGFlow API
        api_key: API key for authentication
        kb_id: Knowledge base ID
        node_id: Node ID
        format: Download format (txt, json, csv, xlsx)
        include_metadata: Whether to include metadata
        
    Returns:
        Downloaded content as bytes
    """
    from .graphrag_sdk import DownloadFormat
    
    sdk = GraphRAGSDKFactory.create_simple(base_url, api_key)
    
    # Convert string format to enum
    format_enum = DownloadFormat(format.lower())
    
    async with sdk:
        content = await sdk.download_node_content(
            kb_id=kb_id,
            node_id=node_id,
            format=format_enum,
            include_metadata=include_metadata
        )
        return content


async def get_graph_overview(
    base_url: str,
    api_key: str,
    kb_id: str
) -> Dict[str, Any]:
    """
    Convenience function to get knowledge graph overview
    
    Args:
        base_url: Base URL of RAGFlow API
        api_key: API key for authentication
        kb_id: Knowledge base ID
        
    Returns:
        Graph overview with statistics
    """
    sdk = GraphRAGSDKFactory.create_simple(base_url, api_key)
    
    async with sdk:
        # Get graph data and statistics
        graph_data = await sdk.get_knowledge_graph(kb_id=kb_id)
        stats = await sdk.get_graph_statistics(kb_id=kb_id)
        
        return {
            'graph': graph_data,
            'statistics': stats
        }


class GraphRAGClient:
    """
    High-level client for GraphRAG operations
    
    This class provides a simplified interface for common GraphRAG operations
    with automatic resource management and error handling.
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: str,
        enable_cache: bool = True,
        enable_rate_limit: bool = True
    ):
        """
        Initialize GraphRAG client
        
        Args:
            base_url: Base URL of RAGFlow API
            api_key: API key for authentication
            enable_cache: Whether to enable caching
            enable_rate_limit: Whether to enable rate limiting
        """
        self.sdk = GraphRAGSDKFactory.create_simple(
            base_url=base_url,
            api_key=api_key,
            enable_cache=enable_cache,
            enable_rate_limit=enable_rate_limit
        )
        self._session_active = False
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.sdk.__aenter__()
        self._session_active = True
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.sdk.__aexit__(exc_type, exc_val, exc_tb)
        self._session_active = False
    
    async def search(
        self,
        kb_id: str,
        query: str = "",
        entity_types: Optional[list] = None,
        page: int = 1,
        page_size: int = 20
    ):
        """Search nodes in knowledge graph"""
        if not self._session_active:
            raise RuntimeError("Client must be used within async context manager")
        
        return await self.sdk.search_nodes(
            kb_id=kb_id,
            query=query,
            entity_types=entity_types,
            page=page,
            page_size=page_size
        )
    
    async def get_files(self, kb_id: str, node_id: str):
        """Get files associated with a node"""
        if not self._session_active:
            raise RuntimeError("Client must be used within async context manager")
        
        return await self.sdk.get_node_associated_files(kb_id=kb_id, node_id=node_id)
    
    async def download(
        self,
        kb_id: str,
        node_id: str,
        format: str = "txt",
        include_metadata: bool = True
    ):
        """Download node content"""
        if not self._session_active:
            raise RuntimeError("Client must be used within async context manager")
        
        from .graphrag_sdk import DownloadFormat
        format_enum = DownloadFormat(format.lower())
        
        return await self.sdk.download_node_content(
            kb_id=kb_id,
            node_id=node_id,
            format=format_enum,
            include_metadata=include_metadata
        )
    
    async def get_graph(self, kb_id: str):
        """Get knowledge graph data"""
        if not self._session_active:
            raise RuntimeError("Client must be used within async context manager")
        
        return await self.sdk.get_knowledge_graph(kb_id=kb_id)
    
    async def get_statistics(self, kb_id: str):
        """Get graph statistics"""
        if not self._session_active:
            raise RuntimeError("Client must be used within async context manager")
        
        return await self.sdk.get_graph_statistics(kb_id=kb_id)
