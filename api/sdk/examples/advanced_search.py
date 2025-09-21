"""
Advanced GraphRAG SDK Search Example

This example demonstrates advanced search capabilities including:
- Complex query patterns
- Entity type combinations
- Result ranking and filtering
- Search result analysis
- Performance optimization

Author: RAGFlow Team
"""

import asyncio
import os
import time
from typing import List, Dict, Any
from collections import defaultdict, Counter
from graphrag_sdk import GraphRAGClient, GraphRAGError, EntityType


class AdvancedSearchAnalyzer:
    """Advanced search result analyzer"""
    
    def __init__(self):
        self.search_history = []
        self.performance_metrics = []
    
    def analyze_results(self, query: str, results, duration: float):
        """Analyze search results and collect metrics"""
        analysis = {
            'query': query,
            'total_results': results.total_count,
            'returned_results': len(results.nodes),
            'duration_ms': duration * 1000,
            'avg_relevance': 0,
            'entity_type_distribution': Counter(),
            'community_distribution': Counter(),
            'top_keywords': []
        }
        
        if results.nodes:
            # Calculate average relevance
            relevance_scores = [node.pagerank for node in results.nodes if node.pagerank]
            if relevance_scores:
                analysis['avg_relevance'] = sum(relevance_scores) / len(relevance_scores)
            
            # Entity type distribution
            for node in results.nodes:
                analysis['entity_type_distribution'][node.entity_type] += 1
            
            # Community distribution
            for node in results.nodes:
                if node.communities:
                    for community in node.communities:
                        analysis['community_distribution'][community] += 1
            
            # Extract keywords from descriptions
            keywords = []
            for node in results.nodes:
                if node.description:
                    # Simple keyword extraction (in production, use NLP libraries)
                    words = node.description.lower().split()
                    keywords.extend([w for w in words if len(w) > 3])
            
            analysis['top_keywords'] = [word for word, count in Counter(keywords).most_common(10)]
        
        self.search_history.append(analysis)
        self.performance_metrics.append(duration)
        
        return analysis
    
    def print_analysis(self, analysis: Dict[str, Any]):
        """Print search analysis results"""
        print(f"\n--- Search Analysis ---")
        print(f"Query: '{analysis['query']}'")
        print(f"Results: {analysis['returned_results']}/{analysis['total_results']}")
        print(f"Duration: {analysis['duration_ms']:.2f}ms")
        print(f"Avg Relevance: {analysis['avg_relevance']:.3f}")
        
        if analysis['entity_type_distribution']:
            print("Entity Types:")
            for entity_type, count in analysis['entity_type_distribution'].most_common():
                print(f"  {entity_type}: {count}")
        
        if analysis['community_distribution']:
            print("Top Communities:")
            for community, count in analysis['community_distribution'].most_common(5):
                print(f"  {community}: {count}")
        
        if analysis['top_keywords']:
            print(f"Keywords: {', '.join(analysis['top_keywords'][:5])}")
    
    def get_performance_summary(self):
        """Get performance summary"""
        if not self.performance_metrics:
            return {}
        
        return {
            'total_searches': len(self.performance_metrics),
            'avg_duration_ms': sum(self.performance_metrics) / len(self.performance_metrics) * 1000,
            'min_duration_ms': min(self.performance_metrics) * 1000,
            'max_duration_ms': max(self.performance_metrics) * 1000,
            'total_results': sum(h['total_results'] for h in self.search_history)
        }


async def semantic_search_example(client: GraphRAGClient, kb_id: str, analyzer: AdvancedSearchAnalyzer):
    """Demonstrate semantic search capabilities"""
    print("=== Semantic Search Example ===")
    
    # Define semantic search queries
    semantic_queries = [
        "machine learning algorithms",
        "natural language processing",
        "computer vision techniques",
        "deep learning neural networks",
        "artificial intelligence applications"
    ]
    
    for query in semantic_queries:
        print(f"\nSearching: '{query}'")
        
        start_time = time.time()
        results = await client.search(
            kb_id=kb_id,
            query=query,
            entity_types=["CONCEPT", "TECHNOLOGY", "PERSON"],
            page=1,
            page_size=10
        )
        duration = time.time() - start_time
        
        analysis = analyzer.analyze_results(query, results, duration)
        analyzer.print_analysis(analysis)
        
        # Show top results
        print("Top Results:")
        for i, node in enumerate(results.nodes[:3], 1):
            relevance = f" (relevance: {node.pagerank:.3f})" if node.pagerank else ""
            print(f"  {i}. {node.id}{relevance}")
            if node.description:
                print(f"     {node.description[:100]}...")


async def entity_relationship_search(client: GraphRAGClient, kb_id: str, analyzer: AdvancedSearchAnalyzer):
    """Search for entities and their relationships"""
    print("\n=== Entity Relationship Search ===")
    
    # Search for people first
    print("Finding key people...")
    start_time = time.time()
    people_results = await client.search(
        kb_id=kb_id,
        query="",
        entity_types=["PERSON"],
        page=1,
        page_size=20
    )
    duration = time.time() - start_time
    
    analysis = analyzer.analyze_results("people search", people_results, duration)
    print(f"Found {people_results.total_count} people in {duration*1000:.2f}ms")
    
    if people_results.nodes:
        # For each person, search for related organizations
        for person in people_results.nodes[:3]:
            print(f"\nSearching for organizations related to {person.id}...")
            
            start_time = time.time()
            org_results = await client.search(
                kb_id=kb_id,
                query=person.id,
                entity_types=["ORGANIZATION"],
                page=1,
                page_size=5
            )
            duration = time.time() - start_time
            
            print(f"  Found {len(org_results.nodes)} related organizations")
            for org in org_results.nodes:
                relevance = f" (relevance: {org.pagerank:.3f})" if org.pagerank else ""
                print(f"    - {org.id}{relevance}")


async def multi_criteria_search(client: GraphRAGClient, kb_id: str, analyzer: AdvancedSearchAnalyzer):
    """Demonstrate multi-criteria search"""
    print("\n=== Multi-Criteria Search ===")
    
    # Define search criteria combinations
    search_criteria = [
        {
            "query": "innovation",
            "entity_types": ["CONCEPT", "TECHNOLOGY"],
            "description": "Innovation concepts and technologies"
        },
        {
            "query": "research",
            "entity_types": ["PERSON", "ORGANIZATION"],
            "description": "Research people and organizations"
        },
        {
            "query": "development",
            "entity_types": ["CONCEPT", "PRODUCT"],
            "description": "Development concepts and products"
        }
    ]
    
    all_results = []
    
    for criteria in search_criteria:
        print(f"\n{criteria['description']}:")
        print(f"Query: '{criteria['query']}', Types: {criteria['entity_types']}")
        
        start_time = time.time()
        results = await client.search(
            kb_id=kb_id,
            query=criteria['query'],
            entity_types=criteria['entity_types'],
            page=1,
            page_size=15
        )
        duration = time.time() - start_time
        
        analysis = analyzer.analyze_results(criteria['query'], results, duration)
        print(f"Results: {len(results.nodes)}/{results.total_count} in {duration*1000:.2f}ms")
        
        all_results.extend(results.nodes)
        
        # Show top results
        for i, node in enumerate(results.nodes[:3], 1):
            relevance = f" (rel: {node.pagerank:.3f})" if node.pagerank else ""
            print(f"  {i}. {node.id} [{node.entity_type}]{relevance}")
    
    # Analyze combined results
    print(f"\nCombined Analysis:")
    print(f"Total unique nodes: {len(set(node.id for node in all_results))}")
    
    # Entity type distribution across all searches
    entity_dist = Counter(node.entity_type for node in all_results)
    print("Entity distribution:")
    for entity_type, count in entity_dist.most_common():
        print(f"  {entity_type}: {count}")


async def performance_comparison(client: GraphRAGClient, kb_id: str, analyzer: AdvancedSearchAnalyzer):
    """Compare performance of different search strategies"""
    print("\n=== Performance Comparison ===")
    
    test_queries = [
        ("broad", ""),  # Empty query - gets all
        ("specific", "machine learning"),
        ("medium", "technology"),
        ("narrow", "deep learning neural networks")
    ]
    
    performance_results = {}
    
    for query_type, query in test_queries:
        print(f"\nTesting {query_type} query: '{query}'")
        
        # Test with different page sizes
        for page_size in [5, 10, 20, 50]:
            start_time = time.time()
            
            results = await client.search(
                kb_id=kb_id,
                query=query,
                page=1,
                page_size=page_size
            )
            
            duration = time.time() - start_time
            
            key = f"{query_type}_size_{page_size}"
            performance_results[key] = {
                'duration_ms': duration * 1000,
                'results_count': len(results.nodes),
                'total_available': results.total_count
            }
            
            print(f"  Page size {page_size}: {duration*1000:.2f}ms, {len(results.nodes)} results")
    
    # Analyze performance patterns
    print("\nPerformance Analysis:")
    for query_type in ["broad", "specific", "medium", "narrow"]:
        durations = [performance_results[f"{query_type}_size_{size}"]['duration_ms'] 
                    for size in [5, 10, 20, 50]]
        avg_duration = sum(durations) / len(durations)
        print(f"  {query_type.capitalize()} queries avg: {avg_duration:.2f}ms")


async def search_result_ranking(client: GraphRAGClient, kb_id: str, analyzer: AdvancedSearchAnalyzer):
    """Analyze search result ranking"""
    print("\n=== Search Result Ranking Analysis ===")
    
    query = "artificial intelligence"
    
    start_time = time.time()
    results = await client.search(
        kb_id=kb_id,
        query=query,
        page=1,
        page_size=20
    )
    duration = time.time() - start_time
    
    analysis = analyzer.analyze_results(query, results, duration)
    
    print(f"Analyzing ranking for query: '{query}'")
    print(f"Retrieved {len(results.nodes)} results in {duration*1000:.2f}ms")
    
    # Analyze ranking by relevance score
    ranked_nodes = sorted(results.nodes, key=lambda x: x.pagerank or 0, reverse=True)
    
    print("\nTop 10 by relevance:")
    for i, node in enumerate(ranked_nodes[:10], 1):
        relevance = node.pagerank or 0
        print(f"  {i:2d}. {node.id[:30]:<30} | {relevance:.4f} | {node.entity_type}")
    
    # Analyze ranking distribution
    relevance_scores = [node.pagerank for node in results.nodes if node.pagerank]
    if relevance_scores:
        print(f"\nRelevance Score Statistics:")
        print(f"  Min: {min(relevance_scores):.4f}")
        print(f"  Max: {max(relevance_scores):.4f}")
        print(f"  Avg: {sum(relevance_scores)/len(relevance_scores):.4f}")
        print(f"  Median: {sorted(relevance_scores)[len(relevance_scores)//2]:.4f}")


async def main():
    """Main function to run advanced search examples"""
    print("GraphRAG SDK Advanced Search Examples")
    print("=" * 50)
    
    # Configuration
    base_url = os.getenv("GRAPHRAG_BASE_URL", "http://localhost:9380")
    api_key = os.getenv("GRAPHRAG_API_KEY", "your-api-key")
    kb_id = "your-knowledge-base-id"
    
    # Initialize analyzer
    analyzer = AdvancedSearchAnalyzer()
    
    try:
        async with GraphRAGClient(base_url, api_key) as client:
            # Run advanced search examples
            await semantic_search_example(client, kb_id, analyzer)
            await entity_relationship_search(client, kb_id, analyzer)
            await multi_criteria_search(client, kb_id, analyzer)
            await performance_comparison(client, kb_id, analyzer)
            await search_result_ranking(client, kb_id, analyzer)
            
            # Print overall performance summary
            print("\n" + "=" * 50)
            print("Performance Summary:")
            summary = analyzer.get_performance_summary()
            for key, value in summary.items():
                print(f"  {key}: {value}")
            
    except GraphRAGError as e:
        print(f"GraphRAG error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    print("\nAdvanced search examples completed!")


if __name__ == "__main__":
    # Set up environment variables if not already set
    if not os.getenv("GRAPHRAG_BASE_URL"):
        os.environ["GRAPHRAG_BASE_URL"] = "http://localhost:9380"
    if not os.getenv("GRAPHRAG_API_KEY"):
        os.environ["GRAPHRAG_API_KEY"] = "demo-api-key"
    
    # Run the examples
    asyncio.run(main())
