"""
Comprehensive test suite for GraphRAG SDK

This module contains unit tests, integration tests, and performance tests
for the GraphRAG SDK to ensure reliability and performance in production.

Author: RAGFlow Team
Version: 1.0.0
"""

import pytest
import asyncio
import json
import time
import os
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

# Import SDK components
from graphrag_sdk import (
    GraphRAGSDK,
    GraphRAGClient,
    GraphRAGError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    NetworkError,
    EntityType,
    DownloadFormat,
    GraphNode,
    SearchResult,
    AssociatedFilesResult
)
from graphrag_sdk.factory import GraphRAGSDKFactory
from graphrag_sdk.config import GraphRAGConfig, ConfigManager
from graphrag_sdk.serialization import OptimizedCacheManager, SerializationFormat, CompressionType


class TestGraphRAGSDK:
    """Test cases for GraphRAG SDK core functionality"""
    
    @pytest.fixture
    def mock_sdk(self):
        """Create a mock SDK instance for testing"""
        return GraphRAGSDK(
            base_url="http://test.example.com",
            api_key="test-api-key"
        )
    
    @pytest.fixture
    def sample_graph_data(self):
        """Sample graph data for testing"""
        return {
            "nodes": [
                {
                    "id": "node1",
                    "entity_type": "PERSON",
                    "description": "Test person",
                    "pagerank": 0.5,
                    "communities": ["community1"]
                },
                {
                    "id": "node2", 
                    "entity_type": "ORGANIZATION",
                    "description": "Test organization",
                    "pagerank": 0.3,
                    "communities": ["community1", "community2"]
                }
            ],
            "edges": [
                {
                    "source": "node1",
                    "target": "node2",
                    "relation": "works_for",
                    "weight": 0.8
                }
            ]
        }
    
    @pytest.fixture
    def sample_search_result(self):
        """Sample search result for testing"""
        nodes = [
            GraphNode(
                id="test_node_1",
                entity_type="CONCEPT",
                description="Test concept 1",
                pagerank=0.7
            ),
            GraphNode(
                id="test_node_2", 
                entity_type="TECHNOLOGY",
                description="Test technology 1",
                pagerank=0.5
            )
        ]
        
        return SearchResult(
            nodes=nodes,
            total_count=2,
            page=1,
            page_size=10,
            has_more=False
        )
    
    def test_sdk_initialization(self):
        """Test SDK initialization with various parameters"""
        # Basic initialization
        sdk = GraphRAGSDK("http://test.com", "api-key")
        assert sdk.base_url == "http://test.com"
        assert sdk.api_key == "api-key"
        
        # With custom parameters
        sdk = GraphRAGSDK(
            "http://test.com",
            "api-key",
            timeout=60,
            max_retries=5
        )
        assert sdk.timeout == 60
        assert sdk.max_retries == 5
    
    def test_validation_methods(self, mock_sdk):
        """Test input validation methods"""
        # Valid inputs
        mock_sdk._validate_kb_id("valid_kb_id")
        mock_sdk._validate_node_id("valid_node_id")
        
        # Invalid inputs
        with pytest.raises(ValidationError):
            mock_sdk._validate_kb_id("")
        
        with pytest.raises(ValidationError):
            mock_sdk._validate_kb_id(None)
        
        with pytest.raises(ValidationError):
            mock_sdk._validate_node_id("")
    
    @pytest.mark.asyncio
    async def test_get_knowledge_graph_success(self, mock_sdk, sample_graph_data):
        """Test successful knowledge graph retrieval"""
        with patch.object(mock_sdk, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = sample_graph_data
            
            result = await mock_sdk.get_knowledge_graph("test_kb")
            
            assert result == sample_graph_data
            mock_request.assert_called_once_with("GET", "/kb/test_kb/knowledge_graph")
    
    @pytest.mark.asyncio
    async def test_search_nodes_success(self, mock_sdk):
        """Test successful node search"""
        mock_response = {
            "nodes": [
                {
                    "id": "node1",
                    "entity_type": "PERSON",
                    "description": "Test person",
                    "pagerank": 0.5
                }
            ],
            "total_count": 1,
            "has_more": False
        }
        
        with patch.object(mock_sdk, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await mock_sdk.search_nodes(
                kb_id="test_kb",
                query="test query",
                entity_types=["PERSON"],
                page=1,
                page_size=10
            )
            
            assert isinstance(result, SearchResult)
            assert len(result.nodes) == 1
            assert result.nodes[0].id == "node1"
            assert result.total_count == 1
    
    @pytest.mark.asyncio
    async def test_search_nodes_validation_error(self, mock_sdk):
        """Test search nodes with invalid parameters"""
        # Invalid page number
        with pytest.raises(ValidationError):
            await mock_sdk.search_nodes("test_kb", page=0)
        
        # Invalid page size
        with pytest.raises(ValidationError):
            await mock_sdk.search_nodes("test_kb", page_size=0)
        
        with pytest.raises(ValidationError):
            await mock_sdk.search_nodes("test_kb", page_size=101)
    
    @pytest.mark.asyncio
    async def test_download_node_content(self, mock_sdk):
        """Test node content download"""
        test_content = b"test content data"
        
        with patch.object(mock_sdk, '_ensure_session', new_callable=AsyncMock), \
             patch.object(mock_sdk, '_check_rate_limit', new_callable=AsyncMock), \
             patch('aiohttp.ClientSession.post') as mock_post:
            
            # Mock response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.read = AsyncMock(return_value=test_content)
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await mock_sdk.download_node_content(
                kb_id="test_kb",
                node_id="test_node",
                format=DownloadFormat.TXT
            )
            
            assert result == test_content


class TestGraphRAGClient:
    """Test cases for GraphRAG Client high-level interface"""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock client for testing"""
        return GraphRAGClient(
            base_url="http://test.example.com",
            api_key="test-api-key"
        )
    
    @pytest.mark.asyncio
    async def test_client_context_manager(self, mock_client):
        """Test client as async context manager"""
        with patch.object(mock_client.sdk, '__aenter__', new_callable=AsyncMock) as mock_enter, \
             patch.object(mock_client.sdk, '__aexit__', new_callable=AsyncMock) as mock_exit:
            
            async with mock_client as client:
                assert client == mock_client
                assert client._session_active
            
            mock_enter.assert_called_once()
            mock_exit.assert_called_once()
            assert not mock_client._session_active
    
    @pytest.mark.asyncio
    async def test_client_search_without_context(self, mock_client):
        """Test client operations without context manager"""
        with pytest.raises(RuntimeError, match="Client must be used within async context manager"):
            await mock_client.search("test_kb", "test_query")


class TestConfiguration:
    """Test cases for configuration management"""
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Valid configuration
        config = GraphRAGConfig(
            base_url="http://test.com",
            api_key="test-key"
        )
        config.validate()  # Should not raise
        
        # Invalid base URL
        with pytest.raises(ValueError, match="base_url is required"):
            GraphRAGConfig(base_url="", api_key="test-key")
        
        # Invalid API key
        with pytest.raises(ValueError, match="api_key is required"):
            GraphRAGConfig(base_url="http://test.com", api_key="")
        
        # Invalid URL format
        with pytest.raises(ValueError, match="base_url must start with"):
            GraphRAGConfig(base_url="invalid-url", api_key="test-key")
    
    def test_config_from_env(self):
        """Test configuration from environment variables"""
        env_vars = {
            "GRAPHRAG_BASE_URL": "http://env.test.com",
            "GRAPHRAG_API_KEY": "env-api-key",
            "GRAPHRAG_CACHE_ENABLED": "true",
            "GRAPHRAG_RATE_LIMIT_MAX_REQUESTS": "200"
        }
        
        with patch.dict(os.environ, env_vars):
            config = ConfigManager.from_env()
            
            assert config.base_url == "http://env.test.com"
            assert config.api_key == "env-api-key"
            assert config.cache.enabled is True
            assert config.rate_limit.max_requests == 200
    
    def test_config_from_dict(self):
        """Test configuration from dictionary"""
        config_dict = {
            "base_url": "http://dict.test.com",
            "api_key": "dict-api-key",
            "cache": {
                "enabled": False,
                "default_ttl": 7200
            },
            "rate_limit": {
                "max_requests": 50,
                "window_seconds": 120
            }
        }
        
        config = ConfigManager.from_dict(config_dict)
        
        assert config.base_url == "http://dict.test.com"
        assert config.api_key == "dict-api-key"
        assert config.cache.enabled is False
        assert config.cache.default_ttl == 7200
        assert config.rate_limit.max_requests == 50
        assert config.rate_limit.window_seconds == 120


class TestSerialization:
    """Test cases for serialization and caching"""
    
    @pytest.fixture
    def sample_data(self):
        """Sample data for serialization testing"""
        return {
            "nodes": [
                {"id": "node1", "type": "PERSON", "data": "test data"},
                {"id": "node2", "type": "ORG", "data": "more test data"}
            ],
            "metadata": {
                "timestamp": "2024-01-01T00:00:00Z",
                "version": "1.0"
            }
        }
    
    @pytest.mark.asyncio
    async def test_cache_operations(self, sample_data):
        """Test basic cache operations"""
        # Mock Redis client
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            
            cache = OptimizedCacheManager(
                redis_url="redis://test",
                serialization_format=SerializationFormat.JSON,
                compression_type=CompressionType.NONE
            )
            
            # Test set operation
            mock_client.pipeline.return_value.execute = AsyncMock(return_value=[True, True])
            result = await cache.set("test_key", sample_data)
            assert result is True
            
            # Test get operation (cache miss)
            mock_client.hgetall.return_value = {}
            result = await cache.get("test_key")
            assert result is None
    
    def test_serialization_formats(self, sample_data):
        """Test different serialization formats"""
        from graphrag_sdk.serialization import JSONSerializer, MessagePackSerializer, PickleSerializer
        
        serializers = [
            JSONSerializer(),
            MessagePackSerializer(),
            PickleSerializer()
        ]
        
        for serializer in serializers:
            # Test serialization round-trip
            serialized = serializer.serialize(sample_data)
            assert isinstance(serialized, bytes)
            
            deserialized = serializer.deserialize(serialized)
            assert deserialized == sample_data
    
    def test_compression_algorithms(self):
        """Test different compression algorithms"""
        from graphrag_sdk.serialization import CompressionManager, CompressionType
        
        test_data = b"This is test data for compression" * 100  # Make it compressible
        
        compression_types = [
            CompressionType.GZIP,
            CompressionType.LZ4,
            CompressionType.ZSTD
        ]
        
        for comp_type in compression_types:
            # Test compression round-trip
            compressed = CompressionManager.compress(test_data, comp_type)
            assert len(compressed) < len(test_data)  # Should be smaller
            
            decompressed = CompressionManager.decompress(compressed, comp_type)
            assert decompressed == test_data


class TestErrorHandling:
    """Test cases for error handling"""
    
    @pytest.mark.asyncio
    async def test_authentication_error(self):
        """Test authentication error handling"""
        sdk = GraphRAGSDK("http://test.com", "invalid-key")
        
        with patch.object(sdk, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = AuthenticationError("Invalid API key")
            
            with pytest.raises(AuthenticationError):
                await sdk.get_knowledge_graph("test_kb")
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        """Test rate limit error handling"""
        sdk = GraphRAGSDK("http://test.com", "test-key")
        
        with patch.object(sdk, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = RateLimitError("Rate limit exceeded")
            
            with pytest.raises(RateLimitError):
                await sdk.search_nodes("test_kb", "test_query")
    
    @pytest.mark.asyncio
    async def test_network_error_retry(self):
        """Test network error retry mechanism"""
        sdk = GraphRAGSDK("http://test.com", "test-key", max_retries=2)
        
        with patch.object(sdk, '_ensure_session', new_callable=AsyncMock), \
             patch.object(sdk, '_check_rate_limit', new_callable=AsyncMock), \
             patch('aiohttp.ClientSession.request') as mock_request:
            
            # Mock network error on first two attempts, success on third
            mock_request.side_effect = [
                Exception("Network error 1"),
                Exception("Network error 2"),
                Mock(status=200, json=AsyncMock(return_value={"retcode": 0, "data": {}}))
            ]
            
            # Should succeed after retries
            result = await sdk._make_request("GET", "/test")
            assert result == {}


class TestPerformance:
    """Performance test cases"""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test concurrent request handling"""
        sdk = GraphRAGSDK("http://test.com", "test-key")
        
        with patch.object(sdk, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"nodes": [], "total_count": 0}
            
            # Create multiple concurrent requests
            tasks = []
            for i in range(10):
                task = sdk.search_nodes(f"kb_{i}", f"query_{i}")
                tasks.append(task)
            
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            duration = time.time() - start_time
            
            assert len(results) == 10
            assert duration < 1.0  # Should complete quickly with mocked requests
    
    @pytest.mark.asyncio
    async def test_large_data_handling(self):
        """Test handling of large data sets"""
        # Create large mock data
        large_data = {
            "nodes": [
                {
                    "id": f"node_{i}",
                    "entity_type": "CONCEPT",
                    "description": f"Large description {i}" * 100
                }
                for i in range(1000)
            ]
        }
        
        sdk = GraphRAGSDK("http://test.com", "test-key")
        
        with patch.object(sdk, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = large_data
            
            start_time = time.time()
            result = await sdk.get_knowledge_graph("test_kb")
            duration = time.time() - start_time
            
            assert len(result["nodes"]) == 1000
            assert duration < 5.0  # Should handle large data efficiently


# Test fixtures and utilities
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
