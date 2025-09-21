"""
Performance and Stress Tests for GraphRAG SDK

This module contains performance benchmarks and stress tests to ensure
the SDK can handle production workloads efficiently.

Author: RAGFlow Team
Version: 1.0.0
"""

import asyncio
import time
import statistics
import psutil
import gc
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
import pytest
import json
import os

from graphrag_sdk import GraphRAGClient, GraphRAGSDK
from graphrag_sdk.factory import GraphRAGSDKFactory
from graphrag_sdk.serialization import OptimizedCacheManager, SerializationFormat, CompressionType


class PerformanceMonitor:
    """Monitor performance metrics during tests"""
    
    def __init__(self):
        self.metrics = []
        self.start_time = None
        self.start_memory = None
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        gc.collect()  # Clean up before test
    
    def record_metric(self, operation: str, duration: float, memory_delta: float = 0):
        """Record a performance metric"""
        self.metrics.append({
            'operation': operation,
            'duration_ms': duration * 1000,
            'memory_delta_mb': memory_delta,
            'timestamp': time.time()
        })
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return summary"""
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        total_duration = end_time - self.start_time if self.start_time else 0
        memory_delta = end_memory - self.start_memory if self.start_memory else 0
        
        durations = [m['duration_ms'] for m in self.metrics]
        
        return {
            'total_duration_s': total_duration,
            'total_memory_delta_mb': memory_delta,
            'operation_count': len(self.metrics),
            'avg_operation_duration_ms': statistics.mean(durations) if durations else 0,
            'min_operation_duration_ms': min(durations) if durations else 0,
            'max_operation_duration_ms': max(durations) if durations else 0,
            'p95_operation_duration_ms': statistics.quantiles(durations, n=20)[18] if len(durations) > 20 else 0,
            'operations_per_second': len(durations) / total_duration if total_duration > 0 else 0
        }


class LoadGenerator:
    """Generate load for stress testing"""
    
    def __init__(self, client: GraphRAGClient, kb_id: str):
        self.client = client
        self.kb_id = kb_id
        self.results = []
    
    async def generate_search_load(
        self,
        queries: List[str],
        concurrent_requests: int = 10,
        duration_seconds: int = 60
    ) -> List[Dict[str, Any]]:
        """Generate search load for specified duration"""
        end_time = time.time() + duration_seconds
        semaphore = asyncio.Semaphore(concurrent_requests)
        
        async def search_worker(query: str) -> Dict[str, Any]:
            async with semaphore:
                start_time = time.time()
                try:
                    result = await self.client.search(
                        kb_id=self.kb_id,
                        query=query,
                        page=1,
                        page_size=20
                    )
                    duration = time.time() - start_time
                    return {
                        'query': query,
                        'success': True,
                        'duration_ms': duration * 1000,
                        'result_count': len(result.nodes),
                        'total_count': result.total_count
                    }
                except Exception as e:
                    duration = time.time() - start_time
                    return {
                        'query': query,
                        'success': False,
                        'duration_ms': duration * 1000,
                        'error': str(e)
                    }
        
        tasks = []
        query_index = 0
        
        while time.time() < end_time:
            query = queries[query_index % len(queries)]
            task = asyncio.create_task(search_worker(query))
            tasks.append(task)
            query_index += 1
            
            # Small delay to control request rate
            await asyncio.sleep(0.1)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return valid results
        valid_results = [r for r in results if isinstance(r, dict)]
        return valid_results


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Performance benchmark tests"""
    
    @pytest.fixture
    def performance_monitor(self):
        """Create performance monitor"""
        return PerformanceMonitor()
    
    @pytest.fixture
    def test_queries(self):
        """Test queries for performance testing"""
        return [
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "neural networks",
            "computer vision",
            "natural language processing",
            "data science",
            "algorithm",
            "technology",
            "innovation"
        ]
    
    @pytest.mark.asyncio
    async def test_search_performance_baseline(self, performance_monitor, test_queries):
        """Baseline search performance test"""
        base_url = os.getenv("GRAPHRAG_BASE_URL", "http://localhost:9380")
        api_key = os.getenv("GRAPHRAG_API_KEY", "test-key")
        kb_id = "test-kb"
        
        performance_monitor.start_monitoring()
        
        async with GraphRAGClient(base_url, api_key) as client:
            for query in test_queries:
                start_time = time.time()
                
                try:
                    result = await client.search(kb_id, query, page_size=20)
                    duration = time.time() - start_time
                    
                    performance_monitor.record_metric(
                        f"search_{query.replace(' ', '_')}",
                        duration
                    )
                    
                    # Verify reasonable performance
                    assert duration < 5.0, f"Search took too long: {duration:.2f}s"
                    
                except Exception as e:
                    duration = time.time() - start_time
                    performance_monitor.record_metric(f"search_error_{query}", duration)
                    pytest.fail(f"Search failed for query '{query}': {e}")
        
        summary = performance_monitor.stop_monitoring()
        
        # Performance assertions
        assert summary['avg_operation_duration_ms'] < 2000, "Average search time too high"
        assert summary['operations_per_second'] > 0.5, "Throughput too low"
        
        print(f"Search Performance Summary: {summary}")
    
    @pytest.mark.asyncio
    async def test_concurrent_search_performance(self, performance_monitor, test_queries):
        """Test concurrent search performance"""
        base_url = os.getenv("GRAPHRAG_BASE_URL", "http://localhost:9380")
        api_key = os.getenv("GRAPHRAG_API_KEY", "test-key")
        kb_id = "test-kb"
        
        performance_monitor.start_monitoring()
        
        async with GraphRAGClient(base_url, api_key) as client:
            # Create concurrent search tasks
            tasks = []
            for i in range(20):  # 20 concurrent searches
                query = test_queries[i % len(test_queries)]
                task = client.search(kb_id, query, page_size=10)
                tasks.append(task)
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_duration = time.time() - start_time
            
            # Analyze results
            successful_results = [r for r in results if not isinstance(r, Exception)]
            failed_results = [r for r in results if isinstance(r, Exception)]
            
            performance_monitor.record_metric("concurrent_search_batch", total_duration)
        
        summary = performance_monitor.stop_monitoring()
        
        # Performance assertions
        assert len(successful_results) >= 18, "Too many failed concurrent requests"
        assert total_duration < 10.0, "Concurrent searches took too long"
        
        print(f"Concurrent Search Results: {len(successful_results)}/{len(tasks)} successful")
        print(f"Concurrent Performance Summary: {summary}")
    
    @pytest.mark.asyncio
    async def test_cache_performance(self, performance_monitor):
        """Test cache performance with different configurations"""
        test_data = {
            "large_dataset": [{"id": f"item_{i}", "data": f"data_{i}" * 100} for i in range(1000)]
        }
        
        cache_configs = [
            (SerializationFormat.JSON, CompressionType.NONE),
            (SerializationFormat.JSON, CompressionType.GZIP),
            (SerializationFormat.MSGPACK, CompressionType.NONE),
            (SerializationFormat.MSGPACK, CompressionType.LZ4),
            (SerializationFormat.PICKLE, CompressionType.ZSTD)
        ]
        
        performance_monitor.start_monitoring()
        
        for serialization, compression in cache_configs:
            # Mock cache manager for testing
            cache = OptimizedCacheManager(
                redis_url="redis://localhost:6379",
                serialization_format=serialization,
                compression_type=compression
            )
            
            # Test serialization performance
            start_time = time.time()
            serialized_data, ser_time, comp_time = await cache._serialize_and_compress(
                test_data, serialization, compression
            )
            total_time = time.time() - start_time
            
            performance_monitor.record_metric(
                f"cache_{serialization.value}_{compression.value}",
                total_time
            )
            
            # Test deserialization performance
            start_time = time.time()
            deserialized_data = await cache._decompress_and_deserialize(
                serialized_data, serialization, compression
            )
            deser_time = time.time() - start_time
            
            performance_monitor.record_metric(
                f"cache_deser_{serialization.value}_{compression.value}",
                deser_time
            )
            
            # Verify data integrity
            assert deserialized_data == test_data
            
            print(f"Cache {serialization.value}/{compression.value}: "
                  f"ser={ser_time*1000:.2f}ms, comp={comp_time*1000:.2f}ms, "
                  f"deser={deser_time*1000:.2f}ms, size={len(serialized_data)} bytes")
        
        summary = performance_monitor.stop_monitoring()
        print(f"Cache Performance Summary: {summary}")


@pytest.mark.stress
class TestStressTests:
    """Stress tests for high load scenarios"""
    
    @pytest.mark.asyncio
    async def test_sustained_load(self):
        """Test sustained load over extended period"""
        base_url = os.getenv("GRAPHRAG_BASE_URL", "http://localhost:9380")
        api_key = os.getenv("GRAPHRAG_API_KEY", "test-key")
        kb_id = "test-kb"
        
        test_queries = [
            "stress test query 1",
            "stress test query 2", 
            "stress test query 3",
            "stress test query 4",
            "stress test query 5"
        ]
        
        async with GraphRAGClient(base_url, api_key) as client:
            load_generator = LoadGenerator(client, kb_id)
            
            # Generate load for 30 seconds with 5 concurrent requests
            results = await load_generator.generate_search_load(
                queries=test_queries,
                concurrent_requests=5,
                duration_seconds=30
            )
            
            # Analyze results
            successful_requests = [r for r in results if r['success']]
            failed_requests = [r for r in results if not r['success']]
            
            success_rate = len(successful_requests) / len(results) if results else 0
            avg_duration = statistics.mean([r['duration_ms'] for r in successful_requests]) if successful_requests else 0
            
            # Stress test assertions
            assert success_rate >= 0.95, f"Success rate too low: {success_rate:.2%}"
            assert avg_duration < 3000, f"Average response time too high: {avg_duration:.2f}ms"
            assert len(results) > 100, "Not enough requests generated"
            
            print(f"Stress Test Results:")
            print(f"  Total requests: {len(results)}")
            print(f"  Successful: {len(successful_requests)}")
            print(f"  Failed: {len(failed_requests)}")
            print(f"  Success rate: {success_rate:.2%}")
            print(f"  Average duration: {avg_duration:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """Test memory usage under sustained load"""
        base_url = os.getenv("GRAPHRAG_BASE_URL", "http://localhost:9380")
        api_key = os.getenv("GRAPHRAG_API_KEY", "test-key")
        kb_id = "test-kb"
        
        # Monitor memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        async with GraphRAGClient(base_url, api_key) as client:
            # Perform many operations to test memory leaks
            for i in range(100):
                try:
                    await client.search(kb_id, f"memory test query {i}", page_size=50)
                    
                    # Check memory every 10 operations
                    if i % 10 == 0:
                        current_memory = process.memory_info().rss / 1024 / 1024
                        memory_growth = current_memory - initial_memory
                        
                        # Memory growth should be reasonable
                        assert memory_growth < 100, f"Excessive memory growth: {memory_growth:.2f}MB"
                        
                except Exception as e:
                    # Some failures are acceptable under stress
                    if i > 50:  # Allow some failures after initial operations
                        continue
                    else:
                        pytest.fail(f"Early failure in memory test: {e}")
        
        # Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024
        total_growth = final_memory - initial_memory
        
        print(f"Memory Usage:")
        print(f"  Initial: {initial_memory:.2f}MB")
        print(f"  Final: {final_memory:.2f}MB")
        print(f"  Growth: {total_growth:.2f}MB")
        
        # Memory growth should be reasonable
        assert total_growth < 50, f"Memory leak detected: {total_growth:.2f}MB growth"
    
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test error recovery under adverse conditions"""
        base_url = os.getenv("GRAPHRAG_BASE_URL", "http://localhost:9380")
        api_key = os.getenv("GRAPHRAG_API_KEY", "test-key")
        kb_id = "test-kb"
        
        async with GraphRAGClient(base_url, api_key) as client:
            # Test with invalid requests mixed with valid ones
            test_cases = [
                ("valid query", True),
                ("", True),  # Empty query should be handled
                ("valid query 2", True),
                ("very long query " * 100, True),  # Very long query
                ("valid query 3", True),
            ]
            
            successful_recoveries = 0
            
            for query, should_succeed in test_cases:
                try:
                    result = await client.search(kb_id, query, page_size=10)
                    if should_succeed:
                        successful_recoveries += 1
                    print(f"Query '{query[:20]}...' succeeded")
                    
                except Exception as e:
                    if should_succeed:
                        print(f"Query '{query[:20]}...' failed: {e}")
                    else:
                        successful_recoveries += 1  # Expected failure
            
            # Should handle most cases gracefully
            recovery_rate = successful_recoveries / len(test_cases)
            assert recovery_rate >= 0.8, f"Poor error recovery: {recovery_rate:.2%}"
            
            print(f"Error Recovery Rate: {recovery_rate:.2%}")


def run_performance_tests():
    """Run all performance tests"""
    print("Running GraphRAG SDK Performance Tests")
    print("=" * 50)
    
    # Run performance benchmarks
    pytest.main([
        __file__ + "::TestPerformanceBenchmarks",
        "-v",
        "-m", "performance",
        "--tb=short"
    ])
    
    print("\n" + "=" * 50)
    print("Performance tests completed!")


def run_stress_tests():
    """Run all stress tests"""
    print("Running GraphRAG SDK Stress Tests")
    print("=" * 50)
    
    # Run stress tests
    pytest.main([
        __file__ + "::TestStressTests",
        "-v", 
        "-m", "stress",
        "--tb=short"
    ])
    
    print("\n" + "=" * 50)
    print("Stress tests completed!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "stress":
        run_stress_tests()
    else:
        run_performance_tests()
