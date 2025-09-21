# GraphRAG SDK

Production-grade SDK for RAGFlow Knowledge Graph functionality. This SDK provides a comprehensive interface for interacting with RAGFlow's GraphRAG features, including knowledge graph construction, node search, file associations, and content download.

## Features

- 🚀 **High Performance**: Optimized for production environments with caching, compression, and connection pooling
- 🔍 **Knowledge Graph Search**: Advanced node search with entity type filtering and pagination
- 📁 **File Associations**: Retrieve documents and text chunks associated with graph nodes
- 💾 **Multiple Download Formats**: Support for TXT, JSON, CSV, and Excel formats
- 🔄 **Intelligent Caching**: Redis-based caching with multiple serialization formats and compression
- 🛡️ **Error Handling**: Comprehensive error handling with retry mechanisms
- 📊 **Performance Monitoring**: Built-in metrics and performance tracking
- 🔐 **Security**: Authentication, rate limiting, and SSL support

## Installation

```bash
pip install ragflow-graphrag-sdk
```

Or install from source:

```bash
git clone https://github.com/ragflow/ragflow.git
cd ragflow/api/sdk
pip install -e .
```

## Quick Start

### Simple Usage

```python
import asyncio
from graphrag_sdk import GraphRAGClient

async def main():
    # Create client
    async with GraphRAGClient("http://localhost:9380", "your-api-key") as client:
        # Search nodes
        results = await client.search("kb_id", "search query")
        print(f"Found {len(results.nodes)} nodes")
        
        # Get associated files for first node
        if results.nodes:
            node_id = results.nodes[0].id
            files = await client.get_files("kb_id", node_id)
            print(f"Node has {files.total_files} associated files")
            
            # Download content
            content = await client.download("kb_id", node_id, format="json")
            print(f"Downloaded {len(content)} bytes")

# Run the example
asyncio.run(main())
```

### Advanced Configuration

```python
from graphrag_sdk import GraphRAGSDKFactory, ConfigManager

# Load configuration from file
config = ConfigManager.from_file("config.json")
sdk = GraphRAGSDKFactory.create_from_config(config)

# Or create with custom settings
from graphrag_sdk import GraphRAGConfig, CacheConfig, RateLimitConfig

config = GraphRAGConfig(
    base_url="http://localhost:9380",
    api_key="your-api-key",
    cache=CacheConfig(
        enabled=True,
        redis_url="redis://localhost:6379",
        default_ttl=3600
    ),
    rate_limit=RateLimitConfig(
        enabled=True,
        max_requests=100,
        window_seconds=60
    )
)

sdk = GraphRAGSDKFactory.create_from_config(config)
```

## Configuration

### Environment Variables

```bash
# Basic configuration
export GRAPHRAG_BASE_URL="http://localhost:9380"
export GRAPHRAG_API_KEY="your-api-key"

# Cache configuration
export GRAPHRAG_CACHE_ENABLED="true"
export GRAPHRAG_REDIS_URL="redis://localhost:6379"
export GRAPHRAG_CACHE_TTL="3600"

# Rate limiting
export GRAPHRAG_RATE_LIMIT_ENABLED="true"
export GRAPHRAG_RATE_LIMIT_MAX_REQUESTS="100"
export GRAPHRAG_RATE_LIMIT_WINDOW="60"

# Retry configuration
export GRAPHRAG_MAX_RETRIES="3"
export GRAPHRAG_INITIAL_DELAY="1.0"
export GRAPHRAG_BACKOFF_FACTOR="2.0"

# Security
export GRAPHRAG_VERIFY_SSL="true"
export GRAPHRAG_TIMEOUT="30"
```

### Configuration File

Create a `graphrag_config.json` file:

```json
{
  "base_url": "http://localhost:9380",
  "api_key": "your-api-key",
  "cache": {
    "enabled": true,
    "redis_url": "redis://localhost:6379",
    "default_ttl": 3600,
    "max_memory": "256mb",
    "eviction_policy": "allkeys-lru"
  },
  "rate_limit": {
    "enabled": true,
    "max_requests": 100,
    "window_seconds": 60,
    "burst_limit": 10
  },
  "retry": {
    "max_retries": 3,
    "initial_delay": 1.0,
    "backoff_factor": 2.0,
    "max_delay": 60.0
  },
  "logging": {
    "level": "INFO",
    "file_path": "/var/log/graphrag.log",
    "max_file_size": "10MB",
    "backup_count": 5
  },
  "security": {
    "verify_ssl": true,
    "timeout": 30,
    "max_connections": 100,
    "max_connections_per_host": 30
  }
}
```

## API Reference

### GraphRAGClient

High-level client for GraphRAG operations.

#### Methods

##### `search(kb_id, query="", entity_types=None, page=1, page_size=20)`

Search nodes in knowledge graph.

**Parameters:**
- `kb_id` (str): Knowledge base ID
- `query` (str): Search query string
- `entity_types` (List[str]): Entity types to filter by
- `page` (int): Page number (1-based)
- `page_size` (int): Results per page (1-100)

**Returns:** `SearchResult` object with nodes and pagination info

**Example:**
```python
results = await client.search(
    kb_id="kb_123",
    query="artificial intelligence",
    entity_types=["CONCEPT", "TECHNOLOGY"],
    page=1,
    page_size=20
)

for node in results.nodes:
    print(f"Node: {node.id}, Type: {node.entity_type}")
```

##### `get_files(kb_id, node_id)`

Get files and chunks associated with a node.

**Parameters:**
- `kb_id` (str): Knowledge base ID
- `node_id` (str): Node ID

**Returns:** `AssociatedFilesResult` object

**Example:**
```python
files = await client.get_files("kb_123", "node_456")
print(f"Files: {files.total_files}, Chunks: {files.total_chunks}")

for file in files.files:
    print(f"File: {file.name}, Type: {file.type}")

for chunk in files.chunks:
    print(f"Chunk: {chunk.docnm_kwd}")
```

##### `download(kb_id, node_id, format="txt", include_metadata=True)`

Download node content in specified format.

**Parameters:**
- `kb_id` (str): Knowledge base ID
- `node_id` (str): Node ID
- `format` (str): Download format ("txt", "json", "csv", "xlsx")
- `include_metadata` (bool): Include metadata in download

**Returns:** `bytes` - Downloaded content

**Example:**
```python
# Download as JSON
content = await client.download("kb_123", "node_456", format="json")
data = json.loads(content.decode('utf-8'))

# Download as CSV
csv_content = await client.download("kb_123", "node_456", format="csv")
with open("node_data.csv", "wb") as f:
    f.write(csv_content)
```

### GraphRAGSDK

Low-level SDK for advanced usage.

#### Methods

##### `get_knowledge_graph(kb_id, use_cache=True)`

Get complete knowledge graph data.

##### `search_nodes(kb_id, query, entity_types, page, page_size, use_cache=True)`

Search nodes with advanced options.

##### `get_node_associated_files(kb_id, node_id, use_cache=True)`

Get associated files for a node.

##### `download_node_content(kb_id, node_id, format, include_metadata, content_type)`

Download node content with detailed options.

##### `get_graph_statistics(kb_id, use_cache=True)`

Get graph statistics and metrics.

## Data Models

### GraphNode

```python
@dataclass
class GraphNode:
    id: str
    entity_type: str
    description: Optional[str] = None
    pagerank: Optional[float] = None
    communities: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
```

### AssociatedFile

```python
@dataclass
class AssociatedFile:
    id: str
    name: str
    type: str
    size: Optional[int] = None
    chunk_num: Optional[int] = None
    create_time: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
```

### TextChunk

```python
@dataclass
class TextChunk:
    id: str
    content: str
    docnm_kwd: str
    page_num_int: Optional[List[int]] = None
    important_kwd: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
```

## Error Handling

The SDK provides comprehensive error handling:

```python
from graphrag_sdk import (
    GraphRAGError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    NetworkError
)

try:
    async with GraphRAGClient(base_url, api_key) as client:
        results = await client.search("kb_id", "query")
except AuthenticationError:
    print("Invalid API key")
except RateLimitError:
    print("Rate limit exceeded")
except ValidationError as e:
    print(f"Invalid input: {e}")
except NetworkError as e:
    print(f"Network error: {e}")
except GraphRAGError as e:
    print(f"GraphRAG error: {e}")
```

## Performance Optimization

### Caching

The SDK uses intelligent caching to improve performance:

```python
# Enable caching (default)
client = GraphRAGClient(base_url, api_key, enable_cache=True)

# Disable caching for real-time data
results = await sdk.search_nodes(kb_id, query, use_cache=False)
```

### Batch Operations

For better performance with multiple operations:

```python
from graphrag_sdk.serialization import OptimizedCacheManager

async with OptimizedCacheManager() as cache:
    # Batch get multiple cached results
    keys = ["search:kb1:query1", "search:kb1:query2"]
    results = await cache.batch_get(keys)
    
    # Batch set multiple results
    items = {"key1": data1, "key2": data2}
    await cache.batch_set(items)
```

### Memory Management

Monitor and optimize memory usage:

```python
# Get performance metrics
metrics = await cache.get_metrics()
print(f"Hit rate: {metrics['hit_rate']:.2%}")
print(f"Memory usage: {metrics['total_size_mb']:.2f} MB")

# Optimize memory
optimization_result = await cache.optimize_memory()
print(f"Memory saved: {optimization_result['memory_saved_mb']:.2f} MB")
```

## Monitoring and Metrics

The SDK provides built-in monitoring capabilities:

```python
# Get cache metrics
metrics = await cache.get_metrics()
print(f"Cache hit rate: {metrics['hit_rate']:.2%}")
print(f"Average serialization time: {metrics['avg_serialization_time_ms']:.2f}ms")

# Monitor API performance
import time

start_time = time.time()
results = await client.search("kb_id", "query")
duration = time.time() - start_time
print(f"Search took {duration:.2f} seconds")
```

## Best Practices

1. **Use Context Managers**: Always use `async with` for proper resource cleanup
2. **Enable Caching**: Use caching for better performance, especially for repeated queries
3. **Handle Errors**: Implement proper error handling for production applications
4. **Monitor Performance**: Use built-in metrics to monitor and optimize performance
5. **Configure Timeouts**: Set appropriate timeouts for your use case
6. **Use Batch Operations**: For multiple operations, use batch methods when available

## Examples

See the `examples/` directory for complete examples:

- `basic_usage.py` - Basic SDK usage
- `advanced_search.py` - Advanced search with filtering
- `batch_operations.py` - Batch operations for performance
- `monitoring.py` - Performance monitoring and metrics
- `error_handling.py` - Comprehensive error handling

## License

Apache 2.0 License. See LICENSE file for details.

## Support

For support and questions:
- GitHub Issues: https://github.com/ragflow/ragflow/issues
- Documentation: https://ragflow.io/docs
- Community: https://discord.gg/ragflow
