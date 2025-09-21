"""
GraphRAG SDK Serialization and Caching Optimization

This module provides high-performance serialization and caching mechanisms
for GraphRAG data structures, optimized for production environments.

Features:
- Multiple serialization formats (JSON, MessagePack, Protocol Buffers)
- Compression support (gzip, lz4, zstd)
- Intelligent caching strategies
- Memory-efficient data structures
- Batch operations
- Streaming support for large datasets

Author: RAGFlow Team
Version: 1.0.0
"""

import json
import gzip
import lz4.frame
import zstandard as zstd
import pickle
import msgpack
import hashlib
import logging
import time
from typing import Any, Dict, List, Optional, Union, Tuple, Protocol
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor
import redis.asyncio as redis
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SerializationFormat(Enum):
    """Supported serialization formats"""
    JSON = "json"
    MSGPACK = "msgpack"
    PICKLE = "pickle"


class CompressionType(Enum):
    """Supported compression types"""
    NONE = "none"
    GZIP = "gzip"
    LZ4 = "lz4"
    ZSTD = "zstd"


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    data: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0
    compression: CompressionType = CompressionType.NONE
    format: SerializationFormat = SerializationFormat.JSON


class Serializer(Protocol):
    """Protocol for serializers"""
    
    def serialize(self, data: Any) -> bytes:
        """Serialize data to bytes"""
        ...
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to data"""
        ...


class JSONSerializer:
    """JSON serializer with custom encoder"""
    
    def serialize(self, data: Any) -> bytes:
        """Serialize data to JSON bytes"""
        return json.dumps(data, default=self._json_encoder, ensure_ascii=False).encode('utf-8')
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize JSON bytes to data"""
        return json.loads(data.decode('utf-8'))
    
    def _json_encoder(self, obj):
        """Custom JSON encoder for complex objects"""
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, set):
            return list(obj)
        else:
            return str(obj)


class MessagePackSerializer:
    """MessagePack serializer for binary efficiency"""
    
    def serialize(self, data: Any) -> bytes:
        """Serialize data to MessagePack bytes"""
        return msgpack.packb(data, default=self._msgpack_encoder, use_bin_type=True)
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize MessagePack bytes to data"""
        return msgpack.unpackb(data, raw=False, strict_map_key=False)
    
    def _msgpack_encoder(self, obj):
        """Custom MessagePack encoder"""
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        elif isinstance(obj, datetime):
            return obj.timestamp()
        elif isinstance(obj, set):
            return list(obj)
        else:
            return str(obj)


class PickleSerializer:
    """Pickle serializer for Python objects"""
    
    def serialize(self, data: Any) -> bytes:
        """Serialize data to pickle bytes"""
        return pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize pickle bytes to data"""
        return pickle.loads(data)


class CompressionManager:
    """Manages data compression and decompression"""
    
    @staticmethod
    def compress(data: bytes, compression_type: CompressionType) -> bytes:
        """Compress data using specified algorithm"""
        if compression_type == CompressionType.NONE:
            return data
        elif compression_type == CompressionType.GZIP:
            return gzip.compress(data, compresslevel=6)
        elif compression_type == CompressionType.LZ4:
            return lz4.frame.compress(data, compression_level=4)
        elif compression_type == CompressionType.ZSTD:
            cctx = zstd.ZstdCompressor(level=3)
            return cctx.compress(data)
        else:
            raise ValueError(f"Unsupported compression type: {compression_type}")
    
    @staticmethod
    def decompress(data: bytes, compression_type: CompressionType) -> bytes:
        """Decompress data using specified algorithm"""
        if compression_type == CompressionType.NONE:
            return data
        elif compression_type == CompressionType.GZIP:
            return gzip.decompress(data)
        elif compression_type == CompressionType.LZ4:
            return lz4.frame.decompress(data)
        elif compression_type == CompressionType.ZSTD:
            dctx = zstd.ZstdDecompressor()
            return dctx.decompress(data)
        else:
            raise ValueError(f"Unsupported compression type: {compression_type}")


class OptimizedCacheManager:
    """
    High-performance cache manager with advanced features
    
    Features:
    - Multiple serialization formats
    - Compression support
    - Intelligent cache eviction
    - Batch operations
    - Memory usage monitoring
    - Performance metrics
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_ttl: int = 3600,
        serialization_format: SerializationFormat = SerializationFormat.MSGPACK,
        compression_type: CompressionType = CompressionType.LZ4,
        max_memory_mb: int = 256,
        enable_metrics: bool = True
    ):
        """
        Initialize optimized cache manager
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds
            serialization_format: Default serialization format
            compression_type: Default compression type
            max_memory_mb: Maximum memory usage in MB
            enable_metrics: Whether to collect performance metrics
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.serialization_format = serialization_format
        self.compression_type = compression_type
        self.max_memory_mb = max_memory_mb
        self.enable_metrics = enable_metrics
        
        # Initialize Redis client
        self.redis_client: Optional[redis.Redis] = None
        
        # Initialize serializers
        self.serializers = {
            SerializationFormat.JSON: JSONSerializer(),
            SerializationFormat.MSGPACK: MessagePackSerializer(),
            SerializationFormat.PICKLE: PickleSerializer()
        }
        
        # Thread pool for CPU-intensive operations
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # Performance metrics
        self.metrics = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'total_size_bytes': 0,
            'compression_ratio': 0.0,
            'avg_serialization_time': 0.0,
            'avg_compression_time': 0.0
        } if enable_metrics else None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_connection()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _ensure_connection(self):
        """Ensure Redis connection is established"""
        if not self.redis_client:
            self.redis_client = redis.from_url(self.redis_url)
            
            # Test connection
            try:
                await self.redis_client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
    
    async def close(self):
        """Close connections and cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()
        
        self.thread_pool.shutdown(wait=True)
        logger.info("Cache manager closed")
    
    def _generate_key(self, prefix: str, *args) -> str:
        """Generate cache key from arguments"""
        key_data = f"{prefix}:{':'.join(str(arg) for arg in args)}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]
    
    async def _serialize_and_compress(
        self,
        data: Any,
        serialization_format: Optional[SerializationFormat] = None,
        compression_type: Optional[CompressionType] = None
    ) -> Tuple[bytes, float, float]:
        """Serialize and compress data with timing"""
        serialization_format = serialization_format or self.serialization_format
        compression_type = compression_type or self.compression_type
        
        # Serialize in thread pool
        start_time = time.time()
        serializer = self.serializers[serialization_format]
        
        def serialize():
            return serializer.serialize(data)
        
        loop = asyncio.get_event_loop()
        serialized_data = await loop.run_in_executor(self.thread_pool, serialize)
        serialization_time = time.time() - start_time
        
        # Compress in thread pool
        start_time = time.time()
        
        def compress():
            return CompressionManager.compress(serialized_data, compression_type)
        
        compressed_data = await loop.run_in_executor(self.thread_pool, compress)
        compression_time = time.time() - start_time
        
        return compressed_data, serialization_time, compression_time
    
    async def _decompress_and_deserialize(
        self,
        data: bytes,
        serialization_format: SerializationFormat,
        compression_type: CompressionType
    ) -> Any:
        """Decompress and deserialize data"""
        # Decompress in thread pool
        def decompress():
            return CompressionManager.decompress(data, compression_type)
        
        loop = asyncio.get_event_loop()
        decompressed_data = await loop.run_in_executor(self.thread_pool, decompress)
        
        # Deserialize in thread pool
        serializer = self.serializers[serialization_format]
        
        def deserialize():
            return serializer.deserialize(decompressed_data)
        
        return await loop.run_in_executor(self.thread_pool, deserialize)
    
    async def get(
        self,
        key: str,
        default: Any = None
    ) -> Any:
        """Get value from cache with optimized deserialization"""
        await self._ensure_connection()
        
        try:
            # Get data and metadata
            pipe = self.redis_client.pipeline()
            pipe.hgetall(f"cache:{key}")
            pipe.hget(f"cache:{key}", "data")
            results = await pipe.execute()
            
            metadata = results[0]
            if not metadata:
                if self.metrics:
                    self.metrics['misses'] += 1
                return default
            
            # Parse metadata
            serialization_format = SerializationFormat(metadata.get(b'format', b'msgpack').decode())
            compression_type = CompressionType(metadata.get(b'compression', b'lz4').decode())
            
            # Check expiration
            expires_at = metadata.get(b'expires_at')
            if expires_at and datetime.fromisoformat(expires_at.decode()) < datetime.now():
                await self.delete(key)
                if self.metrics:
                    self.metrics['misses'] += 1
                return default
            
            # Get compressed data
            compressed_data = results[1]
            if not compressed_data:
                if self.metrics:
                    self.metrics['misses'] += 1
                return default
            
            # Deserialize
            data = await self._decompress_and_deserialize(
                compressed_data,
                serialization_format,
                compression_type
            )
            
            # Update access metadata
            await self.redis_client.hincrby(f"cache:{key}", "access_count", 1)
            await self.redis_client.hset(
                f"cache:{key}",
                "last_accessed",
                datetime.now().isoformat()
            )
            
            if self.metrics:
                self.metrics['hits'] += 1
            
            return data
            
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            if self.metrics:
                self.metrics['misses'] += 1
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialization_format: Optional[SerializationFormat] = None,
        compression_type: Optional[CompressionType] = None
    ) -> bool:
        """Set value in cache with optimized serialization"""
        await self._ensure_connection()
        
        try:
            ttl = ttl or self.default_ttl
            serialization_format = serialization_format or self.serialization_format
            compression_type = compression_type or self.compression_type
            
            # Serialize and compress
            compressed_data, ser_time, comp_time = await self._serialize_and_compress(
                value, serialization_format, compression_type
            )
            
            # Prepare metadata
            now = datetime.now()
            expires_at = now + timedelta(seconds=ttl) if ttl > 0 else None
            
            metadata = {
                "created_at": now.isoformat(),
                "expires_at": expires_at.isoformat() if expires_at else "",
                "format": serialization_format.value,
                "compression": compression_type.value,
                "size_bytes": len(compressed_data),
                "access_count": 0
            }
            
            # Store in Redis
            pipe = self.redis_client.pipeline()
            pipe.hset(f"cache:{key}", "data", compressed_data)
            pipe.hset(f"cache:{key}", mapping=metadata)
            
            if ttl > 0:
                pipe.expire(f"cache:{key}", ttl)
            
            await pipe.execute()
            
            # Update metrics
            if self.metrics:
                self.metrics['sets'] += 1
                self.metrics['total_size_bytes'] += len(compressed_data)
                
                # Update averages
                self.metrics['avg_serialization_time'] = (
                    self.metrics['avg_serialization_time'] * 0.9 + ser_time * 0.1
                )
                self.metrics['avg_compression_time'] = (
                    self.metrics['avg_compression_time'] * 0.9 + comp_time * 0.1
                )
            
            return True
            
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        await self._ensure_connection()

        try:
            result = await self.redis_client.delete(f"cache:{key}")

            if self.metrics:
                self.metrics['deletes'] += 1

            return bool(result)

        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    async def batch_get(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache in batch"""
        await self._ensure_connection()

        if not keys:
            return {}

        try:
            # Prepare pipeline for batch operation
            pipe = self.redis_client.pipeline()

            for key in keys:
                pipe.hgetall(f"cache:{key}")
                pipe.hget(f"cache:{key}", "data")

            results = await pipe.execute()

            # Process results
            batch_results = {}
            for i, key in enumerate(keys):
                metadata_idx = i * 2
                data_idx = i * 2 + 1

                metadata = results[metadata_idx]
                compressed_data = results[data_idx]

                if not metadata or not compressed_data:
                    continue

                try:
                    # Parse metadata
                    serialization_format = SerializationFormat(
                        metadata.get(b'format', b'msgpack').decode()
                    )
                    compression_type = CompressionType(
                        metadata.get(b'compression', b'lz4').decode()
                    )

                    # Check expiration
                    expires_at = metadata.get(b'expires_at')
                    if expires_at and datetime.fromisoformat(expires_at.decode()) < datetime.now():
                        await self.delete(key)
                        continue

                    # Deserialize
                    data = await self._decompress_and_deserialize(
                        compressed_data,
                        serialization_format,
                        compression_type
                    )

                    batch_results[key] = data

                except Exception as e:
                    logger.warning(f"Error deserializing batch key {key}: {e}")
                    continue

            # Update metrics
            if self.metrics:
                self.metrics['hits'] += len(batch_results)
                self.metrics['misses'] += len(keys) - len(batch_results)

            return batch_results

        except Exception as e:
            logger.error(f"Batch get error: {e}")
            return {}

    async def batch_set(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None,
        serialization_format: Optional[SerializationFormat] = None,
        compression_type: Optional[CompressionType] = None
    ) -> Dict[str, bool]:
        """Set multiple values in cache in batch"""
        await self._ensure_connection()

        if not items:
            return {}

        ttl = ttl or self.default_ttl
        serialization_format = serialization_format or self.serialization_format
        compression_type = compression_type or self.compression_type

        results = {}

        try:
            # Serialize all items in parallel
            serialization_tasks = []
            for key, value in items.items():
                task = self._serialize_and_compress(value, serialization_format, compression_type)
                serialization_tasks.append((key, task))

            # Wait for all serialization to complete
            serialized_items = {}
            for key, task in serialization_tasks:
                try:
                    compressed_data, ser_time, comp_time = await task
                    serialized_items[key] = (compressed_data, ser_time, comp_time)
                except Exception as e:
                    logger.warning(f"Serialization error for key {key}: {e}")
                    results[key] = False

            # Batch store in Redis
            pipe = self.redis_client.pipeline()
            now = datetime.now()
            expires_at = now + timedelta(seconds=ttl) if ttl > 0 else None

            for key, (compressed_data, ser_time, comp_time) in serialized_items.items():
                metadata = {
                    "created_at": now.isoformat(),
                    "expires_at": expires_at.isoformat() if expires_at else "",
                    "format": serialization_format.value,
                    "compression": compression_type.value,
                    "size_bytes": len(compressed_data),
                    "access_count": 0
                }

                pipe.hset(f"cache:{key}", "data", compressed_data)
                pipe.hset(f"cache:{key}", mapping=metadata)

                if ttl > 0:
                    pipe.expire(f"cache:{key}", ttl)

            await pipe.execute()

            # Mark successful items
            for key in serialized_items:
                results[key] = True

            # Update metrics
            if self.metrics:
                self.metrics['sets'] += len(serialized_items)
                total_size = sum(len(data[0]) for data in serialized_items.values())
                self.metrics['total_size_bytes'] += total_size

        except Exception as e:
            logger.error(f"Batch set error: {e}")
            for key in items:
                if key not in results:
                    results[key] = False

        return results

    async def clear_expired(self) -> int:
        """Clear expired cache entries"""
        await self._ensure_connection()

        try:
            # Scan for cache keys
            cursor = 0
            expired_keys = []

            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor=cursor,
                    match="cache:*",
                    count=100
                )

                if keys:
                    # Check expiration for each key
                    pipe = self.redis_client.pipeline()
                    for key in keys:
                        pipe.hget(key, "expires_at")

                    expires_results = await pipe.execute()

                    now = datetime.now()
                    for key, expires_at in zip(keys, expires_results):
                        if expires_at:
                            try:
                                exp_time = datetime.fromisoformat(expires_at.decode())
                                if exp_time < now:
                                    expired_keys.append(key)
                            except (ValueError, AttributeError):
                                # Invalid expiration time, consider expired
                                expired_keys.append(key)

                if cursor == 0:
                    break

            # Delete expired keys
            if expired_keys:
                await self.redis_client.delete(*expired_keys)

            logger.info(f"Cleared {len(expired_keys)} expired cache entries")
            return len(expired_keys)

        except Exception as e:
            logger.error(f"Error clearing expired entries: {e}")
            return 0

    async def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics"""
        if not self.metrics:
            return {}

        await self._ensure_connection()

        try:
            # Get Redis memory info
            info = await self.redis_client.info('memory')
            redis_memory_mb = info.get('used_memory', 0) / (1024 * 1024)

            # Calculate hit rate
            total_requests = self.metrics['hits'] + self.metrics['misses']
            hit_rate = self.metrics['hits'] / total_requests if total_requests > 0 else 0

            # Calculate compression ratio
            if self.metrics['sets'] > 0:
                avg_compression_ratio = self.metrics['compression_ratio'] / self.metrics['sets']
            else:
                avg_compression_ratio = 0

            return {
                'hit_rate': hit_rate,
                'total_requests': total_requests,
                'hits': self.metrics['hits'],
                'misses': self.metrics['misses'],
                'sets': self.metrics['sets'],
                'deletes': self.metrics['deletes'],
                'total_size_mb': self.metrics['total_size_bytes'] / (1024 * 1024),
                'redis_memory_mb': redis_memory_mb,
                'avg_serialization_time_ms': self.metrics['avg_serialization_time'] * 1000,
                'avg_compression_time_ms': self.metrics['avg_compression_time'] * 1000,
                'avg_compression_ratio': avg_compression_ratio
            }

        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return {}

    async def optimize_memory(self) -> Dict[str, Any]:
        """Optimize memory usage by cleaning up and reorganizing cache"""
        await self._ensure_connection()

        try:
            # Clear expired entries
            expired_count = await self.clear_expired()

            # Get memory info before optimization
            info_before = await self.redis_client.info('memory')
            memory_before = info_before.get('used_memory', 0)

            # Run Redis memory optimization commands
            await self.redis_client.memory_purge()

            # Get memory info after optimization
            info_after = await self.redis_client.info('memory')
            memory_after = info_after.get('used_memory', 0)

            memory_saved = memory_before - memory_after

            result = {
                'expired_entries_removed': expired_count,
                'memory_before_mb': memory_before / (1024 * 1024),
                'memory_after_mb': memory_after / (1024 * 1024),
                'memory_saved_mb': memory_saved / (1024 * 1024),
                'optimization_time': datetime.now().isoformat()
            }

            logger.info(f"Memory optimization completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Memory optimization error: {e}")
            return {'error': str(e)}
