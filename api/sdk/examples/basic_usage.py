"""
Basic GraphRAG SDK Usage Example

This example demonstrates the basic usage of the GraphRAG SDK,
including searching nodes, getting associated files, and downloading content.

Author: RAGFlow Team
"""

import asyncio
import json
import os
from graphrag_sdk import GraphRAGClient, GraphRAGError


async def basic_search_example():
    """Basic node search example"""
    print("=== Basic Search Example ===")
    
    # Configuration
    base_url = os.getenv("GRAPHRAG_BASE_URL", "http://localhost:9380")
    api_key = os.getenv("GRAPHRAG_API_KEY", "your-api-key")
    kb_id = "your-knowledge-base-id"
    
    try:
        async with GraphRAGClient(base_url, api_key) as client:
            # Search for nodes
            print("Searching for nodes...")
            results = await client.search(
                kb_id=kb_id,
                query="artificial intelligence",
                entity_types=["CONCEPT", "TECHNOLOGY"],
                page=1,
                page_size=10
            )
            
            print(f"Found {len(results.nodes)} nodes (total: {results.total_count})")
            
            # Display results
            for i, node in enumerate(results.nodes[:5], 1):
                print(f"\n{i}. Node ID: {node.id}")
                print(f"   Type: {node.entity_type}")
                print(f"   Description: {node.description[:100] if node.description else 'N/A'}...")
                if node.pagerank:
                    print(f"   Relevance: {node.pagerank:.3f}")
                if node.communities:
                    print(f"   Communities: {', '.join(node.communities[:3])}")
            
            return results.nodes
            
    except GraphRAGError as e:
        print(f"GraphRAG error: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []


async def get_files_example(node_id: str):
    """Get associated files example"""
    print(f"\n=== Associated Files Example for Node: {node_id} ===")
    
    base_url = os.getenv("GRAPHRAG_BASE_URL", "http://localhost:9380")
    api_key = os.getenv("GRAPHRAG_API_KEY", "your-api-key")
    kb_id = "your-knowledge-base-id"
    
    try:
        async with GraphRAGClient(base_url, api_key) as client:
            # Get associated files
            print("Getting associated files...")
            files_result = await client.get_files(kb_id, node_id)
            
            print(f"Total files: {files_result.total_files}")
            print(f"Total chunks: {files_result.total_chunks}")
            
            # Display files
            if files_result.files:
                print("\nAssociated Files:")
                for i, file in enumerate(files_result.files[:5], 1):
                    print(f"{i}. {file.name}")
                    print(f"   Type: {file.type}")
                    print(f"   Size: {file.size if file.size else 'Unknown'} bytes")
                    print(f"   Chunks: {file.chunk_num if file.chunk_num else 'Unknown'}")
                    print(f"   Created: {file.create_time if file.create_time else 'Unknown'}")
            
            # Display chunks
            if files_result.chunks:
                print("\nText Chunks:")
                for i, chunk in enumerate(files_result.chunks[:3], 1):
                    print(f"{i}. Document: {chunk.docnm_kwd}")
                    print(f"   Content preview: {chunk.content[:150]}...")
                    if chunk.important_kwd:
                        print(f"   Keywords: {', '.join(chunk.important_kwd[:5])}")
                    if chunk.page_num_int:
                        print(f"   Pages: {', '.join(map(str, chunk.page_num_int))}")
            
            return files_result
            
    except GraphRAGError as e:
        print(f"GraphRAG error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


async def download_content_example(node_id: str):
    """Download content example"""
    print(f"\n=== Download Content Example for Node: {node_id} ===")
    
    base_url = os.getenv("GRAPHRAG_BASE_URL", "http://localhost:9380")
    api_key = os.getenv("GRAPHRAG_API_KEY", "your-api-key")
    kb_id = "your-knowledge-base-id"
    
    try:
        async with GraphRAGClient(base_url, api_key) as client:
            # Download as JSON
            print("Downloading content as JSON...")
            json_content = await client.download(
                kb_id=kb_id,
                node_id=node_id,
                format="json",
                include_metadata=True
            )
            
            # Parse and display JSON content
            try:
                data = json.loads(json_content.decode('utf-8'))
                print(f"JSON content size: {len(json_content)} bytes")
                print(f"Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                # Save to file
                with open(f"node_{node_id}_content.json", "wb") as f:
                    f.write(json_content)
                print(f"Saved JSON content to node_{node_id}_content.json")
                
            except json.JSONDecodeError:
                print("Downloaded content is not valid JSON")
            
            # Download as TXT
            print("\nDownloading content as TXT...")
            txt_content = await client.download(
                kb_id=kb_id,
                node_id=node_id,
                format="txt",
                include_metadata=False
            )
            
            print(f"TXT content size: {len(txt_content)} bytes")
            print(f"Content preview: {txt_content.decode('utf-8')[:200]}...")
            
            # Save to file
            with open(f"node_{node_id}_content.txt", "wb") as f:
                f.write(txt_content)
            print(f"Saved TXT content to node_{node_id}_content.txt")
            
            # Download as CSV
            print("\nDownloading content as CSV...")
            csv_content = await client.download(
                kb_id=kb_id,
                node_id=node_id,
                format="csv",
                include_metadata=True
            )
            
            print(f"CSV content size: {len(csv_content)} bytes")
            
            # Save to file
            with open(f"node_{node_id}_content.csv", "wb") as f:
                f.write(csv_content)
            print(f"Saved CSV content to node_{node_id}_content.csv")
            
    except GraphRAGError as e:
        print(f"GraphRAG error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


async def pagination_example():
    """Pagination example"""
    print("\n=== Pagination Example ===")
    
    base_url = os.getenv("GRAPHRAG_BASE_URL", "http://localhost:9380")
    api_key = os.getenv("GRAPHRAG_API_KEY", "your-api-key")
    kb_id = "your-knowledge-base-id"
    
    try:
        async with GraphRAGClient(base_url, api_key) as client:
            page = 1
            page_size = 5
            all_nodes = []
            
            print("Fetching all nodes with pagination...")
            
            while True:
                results = await client.search(
                    kb_id=kb_id,
                    query="",  # Empty query to get all nodes
                    page=page,
                    page_size=page_size
                )
                
                print(f"Page {page}: {len(results.nodes)} nodes")
                all_nodes.extend(results.nodes)
                
                if not results.has_more:
                    break
                
                page += 1
                
                # Limit to prevent infinite loop in demo
                if page > 10:
                    print("Stopping at page 10 for demo purposes")
                    break
            
            print(f"\nTotal nodes fetched: {len(all_nodes)}")
            print(f"Total available: {results.total_count}")
            
    except GraphRAGError as e:
        print(f"GraphRAG error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


async def entity_type_filtering_example():
    """Entity type filtering example"""
    print("\n=== Entity Type Filtering Example ===")
    
    base_url = os.getenv("GRAPHRAG_BASE_URL", "http://localhost:9380")
    api_key = os.getenv("GRAPHRAG_API_KEY", "your-api-key")
    kb_id = "your-knowledge-base-id"
    
    entity_types = ["PERSON", "ORGANIZATION", "LOCATION", "CONCEPT", "TECHNOLOGY"]
    
    try:
        async with GraphRAGClient(base_url, api_key) as client:
            for entity_type in entity_types:
                print(f"\nSearching for {entity_type} entities...")
                
                results = await client.search(
                    kb_id=kb_id,
                    query="",
                    entity_types=[entity_type],
                    page=1,
                    page_size=5
                )
                
                print(f"Found {results.total_count} {entity_type} entities")
                
                for node in results.nodes:
                    print(f"  - {node.id}: {node.description[:50] if node.description else 'No description'}...")
                    
    except GraphRAGError as e:
        print(f"GraphRAG error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


async def main():
    """Main function to run all examples"""
    print("GraphRAG SDK Basic Usage Examples")
    print("=" * 50)
    
    # Check environment variables
    if not os.getenv("GRAPHRAG_BASE_URL"):
        print("Warning: GRAPHRAG_BASE_URL not set, using default")
    if not os.getenv("GRAPHRAG_API_KEY"):
        print("Warning: GRAPHRAG_API_KEY not set, using placeholder")
    
    # Run basic search example
    nodes = await basic_search_example()
    
    # If we found nodes, demonstrate file operations
    if nodes:
        first_node = nodes[0]
        await get_files_example(first_node.id)
        await download_content_example(first_node.id)
    
    # Run other examples
    await pagination_example()
    await entity_type_filtering_example()
    
    print("\n" + "=" * 50)
    print("Examples completed!")


if __name__ == "__main__":
    # Set up environment variables if not already set
    if not os.getenv("GRAPHRAG_BASE_URL"):
        os.environ["GRAPHRAG_BASE_URL"] = "http://localhost:9380"
    if not os.getenv("GRAPHRAG_API_KEY"):
        os.environ["GRAPHRAG_API_KEY"] = "demo-api-key"
    
    # Run the examples
    asyncio.run(main())
