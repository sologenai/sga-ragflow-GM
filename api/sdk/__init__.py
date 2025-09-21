"""
GraphRAG SDK - Production-grade SDK for RAGFlow Knowledge Graph functionality

This package provides a comprehensive interface for interacting with RAGFlow's GraphRAG features.

Quick Start:
    from graphrag_sdk import GraphRAGClient
    
    async with GraphRAGClient("http://localhost:9380", "your-api-key") as client:
        # Search nodes
        results = await client.search("kb_id", "search query")
        
        # Get associated files
        files = await client.get_files("kb_id", "node_id")
        
        # Download content
        content = await client.download("kb_id", "node_id", format="json")

Advanced Usage:
    from graphrag_sdk import GraphRAGSDKFactory, ConfigManager
    
    # Create from configuration file
    config = ConfigManager.from_file("config.json")
    sdk = GraphRAGSDKFactory.create_from_config(config)
    
    # Or auto-discover configuration
    sdk = GraphRAGSDKFactory.create_auto()

Author: RAGFlow Team
Version: 1.0.0
License: Apache 2.0
"""

# Core SDK classes
from .graphrag_sdk import (
    GraphRAGSDK,
    GraphRAGError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    NetworkError,
    EntityType,
    DownloadFormat,
    GraphNode,
    GraphEdge,
    AssociatedFile,
    TextChunk,
    SearchResult,
    AssociatedFilesResult,
    CacheManager,
    RateLimiter
)

# Configuration management
from .config import (
    GraphRAGConfig,
    CacheConfig,
    RateLimitConfig,
    RetryConfig,
    LoggingConfig,
    SecurityConfig,
    ConfigManager,
    setup_logging
)

# Factory and convenience functions
from .factory import (
    GraphRAGSDKFactory,
    GraphRAGClient,
    search_knowledge_graph,
    get_node_files,
    download_node_data,
    get_graph_overview
)

# Version information
__version__ = "1.0.0"
__author__ = "RAGFlow Team"
__license__ = "Apache 2.0"

# Public API
__all__ = [
    # Core SDK
    "GraphRAGSDK",
    "GraphRAGClient",
    
    # Exceptions
    "GraphRAGError",
    "AuthenticationError", 
    "RateLimitError",
    "ValidationError",
    "NetworkError",
    
    # Enums
    "EntityType",
    "DownloadFormat",
    
    # Data classes
    "GraphNode",
    "GraphEdge", 
    "AssociatedFile",
    "TextChunk",
    "SearchResult",
    "AssociatedFilesResult",
    
    # Configuration
    "GraphRAGConfig",
    "CacheConfig",
    "RateLimitConfig", 
    "RetryConfig",
    "LoggingConfig",
    "SecurityConfig",
    "ConfigManager",
    
    # Factory
    "GraphRAGSDKFactory",
    
    # Convenience functions
    "search_knowledge_graph",
    "get_node_files",
    "download_node_data", 
    "get_graph_overview",
    
    # Utilities
    "CacheManager",
    "RateLimiter",
    "setup_logging"
]


def get_version():
    """Get SDK version"""
    return __version__


def get_client(base_url: str, api_key: str, **kwargs) -> GraphRAGClient:
    """
    Convenience function to create a GraphRAG client
    
    Args:
        base_url: Base URL of RAGFlow API
        api_key: API key for authentication
        **kwargs: Additional configuration options
        
    Returns:
        GraphRAGClient instance
    """
    return GraphRAGClient(base_url, api_key, **kwargs)


def create_sdk(base_url: str, api_key: str, **kwargs) -> GraphRAGSDK:
    """
    Convenience function to create a GraphRAG SDK instance
    
    Args:
        base_url: Base URL of RAGFlow API
        api_key: API key for authentication
        **kwargs: Additional configuration options
        
    Returns:
        GraphRAGSDK instance
    """
    return GraphRAGSDKFactory.create_simple(base_url, api_key, **kwargs)
