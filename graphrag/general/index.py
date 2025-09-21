#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import json
import logging
import os
from typing import Optional, Dict, Any, List

import networkx as nx
import trio

from api import settings
from api.utils import get_uuid
from api.utils.api_utils import timeout
from graphrag.entity_resolution import EntityResolution
from graphrag.general.community_reports_extractor import CommunityReportsExtractor
from graphrag.general.extractor import Extractor
from graphrag.general.graph_extractor import GraphExtractor as GeneralKGExt
from graphrag.light.graph_extractor import GraphExtractor as LightKGExt
from graphrag.utils import (
    GraphChange,
    chunk_id,
    does_graph_contains,
    get_graph,
    graph_merge,
    set_graph,
    tidy_graph,
)
from rag.nlp import rag_tokenizer, search
from rag.utils.redis_conn import RedisDistributedLock


async def run_graphrag(
    row: dict,
    language: str,
    with_resolution: bool,
    with_community: bool,
    chat_model,
    embedding_model,
    callback,
) -> bool:
    """
    Run GraphRAG processing for a document.

    Args:
        row: Task row containing document and configuration information
        language: Language for processing
        with_resolution: Whether to perform entity resolution
        with_community: Whether to generate community reports
        chat_model: LLM model for chat operations
        embedding_model: Embedding model for vector operations
        callback: Progress callback function

    Returns:
        bool: True if processing completed successfully, False otherwise
    """
    enable_timeout_assertion = os.environ.get("ENABLE_TIMEOUT_ASSERTION")
    start = trio.current_time()

    try:
        # Validate input parameters
        if not row or not isinstance(row, dict):
            raise ValueError("Invalid task row provided")

        tenant_id = row.get("tenant_id")
        kb_id = str(row.get("kb_id", ""))
        doc_id = row.get("doc_id")

        if not all([tenant_id, kb_id, doc_id]):
            raise ValueError(f"Missing required parameters: tenant_id={tenant_id}, kb_id={kb_id}, doc_id={doc_id}")

        # Get GraphRAG configuration with defaults
        graphrag_config = row.get("kb_parser_config", {}).get("graphrag", {})
        entity_types = graphrag_config.get("entity_types", ["organization", "person", "geo", "event", "category"])
        method = graphrag_config.get("method", "light")

        callback(msg=f"Starting GraphRAG processing for doc {doc_id} with method={method}")

        # Retrieve document chunks
        chunks = []
        try:
            for d in settings.retrievaler.chunk_list(doc_id, tenant_id, [kb_id], fields=["content_with_weight", "doc_id"]):
                chunks.append(d["content_with_weight"])
        except Exception as e:
            logging.error(f"Failed to retrieve chunks for doc {doc_id}: {e}")
            callback(msg=f"Error retrieving chunks: {str(e)}")
            return False

        if not chunks:
            callback(msg=f"No chunks found for doc {doc_id}, skipping GraphRAG processing")
            return True

        callback(msg=f"Retrieved {len(chunks)} chunks for processing")

        # Generate subgraph with timeout
        extractor_class = GeneralKGExt if method == "general" else LightKGExt
        timeout_seconds = max(120, len(chunks) * 60 * 10) if enable_timeout_assertion else 10000000000

        with trio.fail_after(timeout_seconds):
            subgraph = await generate_subgraph(
                extractor_class,
                tenant_id,
                kb_id,
                doc_id,
                chunks,
                language,
                entity_types,
                chat_model,
                embedding_model,
                callback,
            )

        if not subgraph:
            callback(msg=f"No subgraph generated for doc {doc_id}")
            return True

        # Acquire distributed lock for graph operations
        graphrag_task_lock = RedisDistributedLock(f"graphrag_task_{kb_id}", lock_value=doc_id, timeout=1200)
        await graphrag_task_lock.spin_acquire()
        callback(msg=f"Acquired GraphRAG task lock for kb {kb_id}")

        try:
            # Merge subgraph into global graph
            subgraph_nodes = set(subgraph.nodes())
            new_graph = await merge_subgraph(
                tenant_id,
                kb_id,
                doc_id,
                subgraph,
                embedding_model,
                callback,
            )

            if new_graph is None:
                raise RuntimeError("Failed to merge subgraph into global graph")

            # Perform entity resolution if requested
            if with_resolution:
                await graphrag_task_lock.spin_acquire()
                callback(msg=f"Starting entity resolution for doc {doc_id}")
                await resolve_entities(
                    new_graph,
                    subgraph_nodes,
                    tenant_id,
                    kb_id,
                    doc_id,
                    chat_model,
                    embedding_model,
                    callback,
                )

            # Generate community reports if requested
            if with_community:
                await graphrag_task_lock.spin_acquire()
                callback(msg=f"Starting community report generation for doc {doc_id}")
                await extract_community(
                    new_graph,
                    tenant_id,
                    kb_id,
                    doc_id,
                    chat_model,
                    embedding_model,
                    callback,
                )

        finally:
            graphrag_task_lock.release()

        processing_time = trio.current_time() - start
        callback(msg=f"GraphRAG processing completed for doc {doc_id} in {processing_time:.2f} seconds")
        return True

    except Exception as e:
        processing_time = trio.current_time() - start
        error_msg = f"GraphRAG processing failed for doc {doc_id} after {processing_time:.2f} seconds: {str(e)}"
        logging.error(error_msg, exc_info=True)
        callback(msg=error_msg)
        return False


async def generate_subgraph(
    extractor: Extractor,
    tenant_id: str,
    kb_id: str,
    doc_id: str,
    chunks: list[str],
    language: str,
    entity_types: list[str],
    llm_bdl,
    embedding_model,
    callback,
) -> nx.Graph:
    """
    Generate a subgraph from document chunks using entity and relation extraction.

    Args:
        extractor: The extractor class to use (GeneralKGExt or LightKGExt)
        tenant_id: Tenant identifier
        kb_id: Knowledge base identifier
        doc_id: Document identifier
        chunks: List of text chunks to process
        language: Language for processing
        entity_types: List of entity types to extract
        llm_bdl: LLM model bundle
        embedding_model: Embedding model for vector operations
        callback: Progress callback function

    Returns:
        nx.Graph: Generated subgraph or None if already exists
    """
    try:
        # Check if graph already contains this document
        contains = await does_graph_contains(tenant_id, kb_id, doc_id)
        if contains:
            callback(msg=f"Graph already contains doc {doc_id}, skipping subgraph generation")
            return None

        start = trio.current_time()
        callback(msg=f"Starting subgraph generation for doc {doc_id} with {len(chunks)} chunks")

        # Validate inputs
        if not chunks:
            callback(msg=f"No chunks provided for doc {doc_id}")
            return None

        if not entity_types:
            entity_types = ["organization", "person", "geo", "event", "category"]
            callback(msg=f"Using default entity types: {entity_types}")

        # Initialize extractor
        ext = extractor(
            llm_bdl,
            language=language,
            entity_types=entity_types,
        )

        # Extract entities and relations
        callback(msg=f"Extracting entities and relations from {len(chunks)} chunks")
        ents, rels = await ext(doc_id, chunks, callback)

        if not ents and not rels:
            callback(msg=f"No entities or relations extracted from doc {doc_id}")
            return None

        callback(msg=f"Extracted {len(ents)} entities and {len(rels)} relations")

        # Build subgraph
        subgraph = nx.Graph()

        # Add entities as nodes
        valid_entities = 0
        for ent in ents:
            try:
                if "description" not in ent:
                    logging.warning(f"Entity {ent} missing description, skipping")
                    continue
                if "entity_name" not in ent:
                    logging.warning(f"Entity {ent} missing entity_name, skipping")
                    continue

                ent["source_id"] = [doc_id]
                subgraph.add_node(ent["entity_name"], **ent)
                valid_entities += 1
            except Exception as e:
                logging.error(f"Error adding entity {ent}: {e}")
                continue

        # Add relations as edges
        valid_relations = 0
        ignored_rels = 0
        for rel in rels:
            try:
                if "description" not in rel:
                    logging.warning(f"Relation {rel} missing description, skipping")
                    continue
                if "src_id" not in rel or "tgt_id" not in rel:
                    logging.warning(f"Relation {rel} missing src_id or tgt_id, skipping")
                    continue

                if not subgraph.has_node(rel["src_id"]) or not subgraph.has_node(rel["tgt_id"]):
                    ignored_rels += 1
                    continue

                rel["source_id"] = [doc_id]
                subgraph.add_edge(
                    rel["src_id"],
                    rel["tgt_id"],
                    **rel,
                )
                valid_relations += 1
            except Exception as e:
                logging.error(f"Error adding relation {rel}: {e}")
                ignored_rels += 1
                continue

        if ignored_rels > 0:
            callback(msg=f"Ignored {ignored_rels} relations due to missing entities or errors")

        callback(msg=f"Built subgraph with {valid_entities} nodes and {valid_relations} edges")

        # Validate and clean the graph
        tidy_graph(subgraph, callback, check_attribute=False)

        if len(subgraph.nodes) == 0:
            callback(msg=f"No valid nodes in subgraph for doc {doc_id}")
            return None

        # Store subgraph metadata
        subgraph.graph["source_id"] = [doc_id]

        # Serialize and store subgraph
        try:
            chunk = {
                "content_with_weight": json.dumps(nx.node_link_data(subgraph, edges="edges"), ensure_ascii=False),
                "knowledge_graph_kwd": "subgraph",
                "kb_id": kb_id,
                "source_id": [doc_id],
                "available_int": 0,
                "removed_kwd": "N",
            }
            cid = chunk_id(chunk)

            # Delete existing subgraph for this document
            await trio.to_thread.run_sync(
                settings.docStoreConn.delete,
                {"knowledge_graph_kwd": "subgraph", "source_id": doc_id},
                search.index_name(tenant_id),
                kb_id
            )

            # Insert new subgraph
            await trio.to_thread.run_sync(
                settings.docStoreConn.insert,
                [{"id": cid, **chunk}],
                search.index_name(tenant_id),
                kb_id
            )

        except Exception as e:
            logging.error(f"Failed to store subgraph for doc {doc_id}: {e}")
            raise

        processing_time = trio.current_time() - start
        callback(msg=f"Generated subgraph for doc {doc_id} in {processing_time:.2f} seconds")
        return subgraph

    except Exception as e:
        error_msg = f"Failed to generate subgraph for doc {doc_id}: {str(e)}"
        logging.error(error_msg, exc_info=True)
        callback(msg=error_msg)
        return None


@timeout(60 * 5)  # Increased timeout for large graphs
async def merge_subgraph(
    tenant_id: str,
    kb_id: str,
    doc_id: str,
    subgraph: nx.Graph,
    embedding_model,
    callback,
) -> nx.Graph:
    """
    Merge a document subgraph into the global knowledge graph.

    Args:
        tenant_id: Tenant identifier
        kb_id: Knowledge base identifier
        doc_id: Document identifier
        subgraph: The subgraph to merge
        embedding_model: Embedding model for vector operations
        callback: Progress callback function

    Returns:
        nx.Graph: The merged global graph
    """
    start = trio.current_time()

    try:
        if not subgraph or len(subgraph.nodes) == 0:
            raise ValueError(f"Empty or invalid subgraph provided for doc {doc_id}")

        callback(msg=f"Starting merge of subgraph for doc {doc_id} with {len(subgraph.nodes)} nodes and {len(subgraph.edges)} edges")

        change = GraphChange()

        # Get existing global graph
        old_graph = await get_graph(tenant_id, kb_id, subgraph.graph["source_id"])

        if old_graph is not None:
            callback(msg=f"Merging with existing graph containing {len(old_graph.nodes)} nodes and {len(old_graph.edges)} edges")

            # Clean the existing graph
            tidy_graph(old_graph, callback)

            # Merge graphs
            new_graph = graph_merge(old_graph, subgraph, change)
        else:
            callback(msg="Creating new global graph from subgraph")
            new_graph = subgraph.copy()
            change.added_updated_nodes = set(new_graph.nodes())
            change.added_updated_edges = set(new_graph.edges())

        # Calculate PageRank for node importance
        callback(msg="Calculating PageRank scores")
        try:
            pr = nx.pagerank(new_graph, max_iter=100, tol=1e-6)
            for node_name, pagerank in pr.items():
                new_graph.nodes[node_name]["pagerank"] = pagerank
        except Exception as e:
            logging.warning(f"PageRank calculation failed: {e}, using default values")
            for node_name in new_graph.nodes():
                new_graph.nodes[node_name]["pagerank"] = 0.0

        # Store the updated graph
        await set_graph(tenant_id, kb_id, embedding_model, new_graph, change, callback)

        processing_time = trio.current_time() - start
        callback(msg=f"Successfully merged subgraph for doc {doc_id} into global graph in {processing_time:.2f} seconds")
        callback(msg=f"Global graph now contains {len(new_graph.nodes)} nodes and {len(new_graph.edges)} edges")

        return new_graph

    except Exception as e:
        processing_time = trio.current_time() - start
        error_msg = f"Failed to merge subgraph for doc {doc_id} after {processing_time:.2f} seconds: {str(e)}"
        logging.error(error_msg, exc_info=True)
        callback(msg=error_msg)
        raise


@timeout(60 * 30, 1)
async def resolve_entities(
    graph: nx.Graph,
    subgraph_nodes: set[str],
    tenant_id: str,
    kb_id: str,
    doc_id: str,
    llm_bdl,
    embedding_model,
    callback,
) -> None:
    """
    Perform entity resolution to merge similar entities in the graph.

    Args:
        graph: The knowledge graph to process
        subgraph_nodes: Set of nodes from the current subgraph
        tenant_id: Tenant identifier
        kb_id: Knowledge base identifier
        doc_id: Document identifier (for logging)
        llm_bdl: LLM model bundle
        embedding_model: Embedding model for vector operations
        callback: Progress callback function
    """
    start = trio.current_time()

    try:
        if not graph or len(graph.nodes) == 0:
            callback(msg="No graph provided for entity resolution")
            return

        if not subgraph_nodes:
            callback(msg="No subgraph nodes provided for entity resolution")
            return

        callback(msg=f"Starting entity resolution for {len(subgraph_nodes)} new nodes in graph with {len(graph.nodes)} total nodes")

        # Initialize entity resolution
        er = EntityResolution(llm_bdl)

        # Perform entity resolution
        reso = await er(graph, subgraph_nodes, callback=callback)

        if not reso:
            callback(msg="Entity resolution returned no results")
            return

        graph = reso.graph
        change = reso.change

        callback(msg=f"Entity resolution removed {len(change.removed_nodes)} nodes and {len(change.removed_edges)} edges")

        # Update PageRank after entity resolution
        try:
            pr = nx.pagerank(graph, max_iter=100, tol=1e-6)
            for node_name, pagerank in pr.items():
                graph.nodes[node_name]["pagerank"] = pagerank
            callback(msg="Updated PageRank scores after entity resolution")
        except Exception as e:
            logging.warning(f"PageRank calculation failed after entity resolution: {e}")

        # Store the updated graph
        await set_graph(tenant_id, kb_id, embedding_model, graph, change, callback)

        processing_time = trio.current_time() - start
        callback(msg=f"Entity resolution completed in {processing_time:.2f} seconds")

    except Exception as e:
        processing_time = trio.current_time() - start
        error_msg = f"Entity resolution failed after {processing_time:.2f} seconds: {str(e)}"
        logging.error(error_msg, exc_info=True)
        callback(msg=error_msg)
        raise


@timeout(60 * 30, 1)
async def extract_community(
    graph: nx.Graph,
    tenant_id: str,
    kb_id: str,
    doc_id: str,
    llm_bdl,
    embedding_model,
    callback,
) -> tuple[list, list]:
    """
    Extract community reports from the knowledge graph.

    Args:
        graph: The knowledge graph to process
        tenant_id: Tenant identifier
        kb_id: Knowledge base identifier
        doc_id: Document identifier (for logging)
        llm_bdl: LLM model bundle
        embedding_model: Embedding model for vector operations
        callback: Progress callback function

    Returns:
        tuple: (community_structure, community_reports)
    """
    start = trio.current_time()

    try:
        if not graph or len(graph.nodes) == 0:
            callback(msg="No graph provided for community extraction")
            return [], []

        callback(msg=f"Starting community extraction for graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges")

        # Initialize community reports extractor
        ext = CommunityReportsExtractor(llm_bdl)

        # Extract communities
        cr = await ext(graph, callback=callback)

        if not cr or not cr.structured_output:
            callback(msg="No communities extracted from graph")
            return [], []

        community_structure = cr.structured_output
        community_reports = cr.output
        doc_ids = graph.graph.get("source_id", [])

        extraction_time = trio.current_time() - start
        callback(msg=f"Extracted {len(community_structure)} communities in {extraction_time:.2f} seconds")

        # Prepare community report chunks for storage
        start_indexing = trio.current_time()
        chunks = []

        for stru, rep in zip(community_structure, community_reports):
            try:
                obj = {
                    "report": rep,
                    "evidences": "\n".join([f.get("explanation", "") for f in stru.get("findings", [])]),
                }

                chunk = {
                    "id": get_uuid(),
                    "docnm_kwd": stru.get("title", "Untitled Community"),
                    "title_tks": rag_tokenizer.tokenize(stru.get("title", "")),
                    "content_with_weight": json.dumps(obj, ensure_ascii=False),
                    "content_ltks": rag_tokenizer.tokenize(obj["report"] + " " + obj["evidences"]),
                    "knowledge_graph_kwd": "community_report",
                    "weight_flt": stru.get("weight", 0.0),
                    "entities_kwd": stru.get("entities", []),
                    "important_kwd": stru.get("entities", []),
                    "kb_id": kb_id,
                    "source_id": list(doc_ids),
                    "available_int": 0,
                }
                chunk["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(chunk["content_ltks"])
                chunks.append(chunk)

            except Exception as e:
                logging.error(f"Error processing community report: {e}")
                continue

        if not chunks:
            callback(msg="No valid community report chunks generated")
            return community_structure, community_reports

        # Delete existing community reports
        try:
            await trio.to_thread.run_sync(
                lambda: settings.docStoreConn.delete(
                    {"knowledge_graph_kwd": "community_report", "kb_id": kb_id},
                    search.index_name(tenant_id),
                    kb_id,
                )
            )
        except Exception as e:
            logging.warning(f"Failed to delete existing community reports: {e}")

        # Insert new community reports in batches
        es_bulk_size = 4
        successful_inserts = 0

        for b in range(0, len(chunks), es_bulk_size):
            try:
                batch = chunks[b : b + es_bulk_size]
                doc_store_result = await trio.to_thread.run_sync(
                    lambda: settings.docStoreConn.insert(batch, search.index_name(tenant_id), kb_id)
                )

                if doc_store_result:
                    error_message = f"Insert chunk error: {doc_store_result}, please check log file and Elasticsearch/Infinity status!"
                    logging.error(error_message)
                    raise Exception(error_message)

                successful_inserts += len(batch)

            except Exception as e:
                logging.error(f"Failed to insert community report batch {b//es_bulk_size + 1}: {e}")
                continue

        indexing_time = trio.current_time() - start_indexing
        total_time = trio.current_time() - start

        callback(msg=f"Successfully indexed {successful_inserts}/{len(chunks)} community reports in {indexing_time:.2f} seconds")
        callback(msg=f"Community extraction completed in {total_time:.2f} seconds")

        return community_structure, community_reports

    except Exception as e:
        processing_time = trio.current_time() - start
        error_msg = f"Community extraction failed after {processing_time:.2f} seconds: {str(e)}"
        logging.error(error_msg, exc_info=True)
        callback(msg=error_msg)
        raise
