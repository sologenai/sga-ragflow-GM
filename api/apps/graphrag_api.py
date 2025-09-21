"""
GraphRAG API Routes

This module provides REST API endpoints for GraphRAG functionality,
integrating the GraphRAG SDK with RAGFlow's API infrastructure.

Author: RAGFlow Team
Version: 1.0.0
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
import io
import json
import csv

from api.db import StatusEnum
from api.db.db_models import Knowledgebase
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.utils import get_uuid, get_format_time
from api.utils.api_utils import server_error_response, validate_request
from api.utils.file_utils import filename_type, thumbnail
from sdk.graphrag_sdk import GraphRAGSDK, GraphRAGError, EntityType, DownloadFormat
from sdk.factory import GraphRAGSDKFactory
from sdk.config import ConfigManager

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
graphrag_bp = Blueprint('graphrag', __name__, url_prefix='/api/v1/graphrag')


def get_sdk_instance() -> GraphRAGSDK:
    """Get GraphRAG SDK instance from application context"""
    if not hasattr(current_app, 'graphrag_sdk'):
        # Initialize SDK from configuration
        try:
            config = ConfigManager.from_env()
            current_app.graphrag_sdk = GraphRAGSDKFactory.create_from_config(config)
        except Exception as e:
            logger.error(f"Failed to initialize GraphRAG SDK: {e}")
            # Fallback to simple configuration
            base_url = current_app.config.get('GRAPHRAG_BASE_URL', 'http://localhost:9380')
            api_key = current_app.config.get('GRAPHRAG_API_KEY', 'default-key')
            current_app.graphrag_sdk = GraphRAGSDKFactory.create_simple(base_url, api_key)
    
    return current_app.graphrag_sdk


def validate_kb_access(kb_id: str) -> Knowledgebase:
    """Validate knowledge base access for current user"""
    kb = KnowledgebaseService.query(
        id=kb_id,
        tenant_id=current_user.id,
        status=StatusEnum.VALID.value
    )
    if not kb:
        raise ValueError(f"Knowledge base not found or access denied: {kb_id}")
    return kb[0]


@graphrag_bp.route('/kb/<kb_id>/graph', methods=['GET'])
@login_required
@validate_request("kb_id")
def get_knowledge_graph(kb_id: str):
    """
    Get knowledge graph for a knowledge base
    
    Args:
        kb_id: Knowledge base ID
        
    Returns:
        Knowledge graph data with nodes and edges
    """
    try:
        # Validate access
        kb = validate_kb_access(kb_id)
        
        # Get SDK instance
        sdk = get_sdk_instance()
        
        # Get graph data
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async def get_graph():
                async with sdk:
                    return await sdk.get_knowledge_graph(kb_id, use_cache=True)
            
            graph_data = loop.run_until_complete(get_graph())
            
            return jsonify({
                "retcode": 0,
                "retmsg": "success",
                "data": {
                    "graph": graph_data,
                    "kb_info": {
                        "id": kb.id,
                        "name": kb.name,
                        "description": kb.description,
                        "created_time": get_format_time(kb.create_time),
                        "updated_time": get_format_time(kb.update_time)
                    }
                }
            })
        finally:
            loop.close()
            
    except ValueError as e:
        return jsonify({"retcode": 102, "retmsg": str(e)}), 404
    except GraphRAGError as e:
        logger.error(f"GraphRAG error in get_knowledge_graph: {e}")
        return server_error_response(e)
    except Exception as e:
        logger.error(f"Unexpected error in get_knowledge_graph: {e}")
        return server_error_response(e)


@graphrag_bp.route('/kb/<kb_id>/search', methods=['POST'])
@login_required
@validate_request("kb_id")
def search_nodes(kb_id: str):
    """
    Search nodes in knowledge graph
    
    Args:
        kb_id: Knowledge base ID
        
    Request Body:
        {
            "query": "search query",
            "entity_types": ["PERSON", "ORGANIZATION"],
            "page": 1,
            "page_size": 20
        }
        
    Returns:
        Search results with nodes and pagination info
    """
    try:
        # Validate access
        kb = validate_kb_access(kb_id)
        
        # Parse request data
        data = request.get_json() or {}
        query = data.get('query', '')
        entity_types = data.get('entity_types', [])
        page = max(1, data.get('page', 1))
        page_size = min(100, max(1, data.get('page_size', 20)))
        
        # Validate entity types
        valid_entity_types = [e.value for e in EntityType]
        entity_types = [et for et in entity_types if et in valid_entity_types]
        
        # Get SDK instance
        sdk = get_sdk_instance()
        
        # Search nodes
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async def search():
                async with sdk:
                    return await sdk.search_nodes(
                        kb_id=kb_id,
                        query=query,
                        entity_types=entity_types,
                        page=page,
                        page_size=page_size,
                        use_cache=True
                    )
            
            search_result = loop.run_until_complete(search())
            
            return jsonify({
                "retcode": 0,
                "retmsg": "success",
                "data": {
                    "nodes": [node.__dict__ for node in search_result.nodes],
                    "total_count": search_result.total_count,
                    "page": search_result.page,
                    "page_size": search_result.page_size,
                    "has_more": search_result.has_more,
                    "query_info": {
                        "query": query,
                        "entity_types": entity_types,
                        "kb_id": kb_id
                    }
                }
            })
        finally:
            loop.close()
            
    except ValueError as e:
        return jsonify({"retcode": 102, "retmsg": str(e)}), 404
    except GraphRAGError as e:
        logger.error(f"GraphRAG error in search_nodes: {e}")
        return server_error_response(e)
    except Exception as e:
        logger.error(f"Unexpected error in search_nodes: {e}")
        return server_error_response(e)


@graphrag_bp.route('/kb/<kb_id>/node/<node_id>/files', methods=['GET'])
@login_required
@validate_request("kb_id", "node_id")
def get_node_files(kb_id: str, node_id: str):
    """
    Get files and chunks associated with a node
    
    Args:
        kb_id: Knowledge base ID
        node_id: Node ID
        
    Returns:
        Associated files and text chunks
    """
    try:
        # Validate access
        kb = validate_kb_access(kb_id)
        
        # Get SDK instance
        sdk = get_sdk_instance()
        
        # Get associated files
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async def get_files():
                async with sdk:
                    return await sdk.get_node_associated_files(
                        kb_id=kb_id,
                        node_id=node_id,
                        use_cache=True
                    )
            
            files_result = loop.run_until_complete(get_files())
            
            return jsonify({
                "retcode": 0,
                "retmsg": "success",
                "data": {
                    "files": [file.__dict__ for file in files_result.files],
                    "chunks": [chunk.__dict__ for chunk in files_result.chunks],
                    "total_files": files_result.total_files,
                    "total_chunks": files_result.total_chunks,
                    "node_info": {
                        "id": node_id,
                        "kb_id": kb_id
                    }
                }
            })
        finally:
            loop.close()
            
    except ValueError as e:
        return jsonify({"retcode": 102, "retmsg": str(e)}), 404
    except GraphRAGError as e:
        logger.error(f"GraphRAG error in get_node_files: {e}")
        return server_error_response(e)
    except Exception as e:
        logger.error(f"Unexpected error in get_node_files: {e}")
        return server_error_response(e)


@graphrag_bp.route('/kb/<kb_id>/node/<node_id>/download', methods=['POST'])
@login_required
@validate_request("kb_id", "node_id")
def download_node_content(kb_id: str, node_id: str):
    """
    Download node content in specified format
    
    Args:
        kb_id: Knowledge base ID
        node_id: Node ID
        
    Request Body:
        {
            "format": "txt|json|csv|xlsx",
            "include_metadata": true,
            "content_type": "chunks|files|all"
        }
        
    Returns:
        File download response
    """
    try:
        # Validate access
        kb = validate_kb_access(kb_id)
        
        # Parse request data
        data = request.get_json() or {}
        format_str = data.get('format', 'txt').lower()
        include_metadata = data.get('include_metadata', True)
        content_type = data.get('content_type', 'chunks')
        
        # Validate format
        try:
            download_format = DownloadFormat(format_str)
        except ValueError:
            return jsonify({
                "retcode": 400,
                "retmsg": f"Invalid format: {format_str}. Supported: txt, json, csv, xlsx"
            }), 400
        
        # Get SDK instance
        sdk = get_sdk_instance()
        
        # Download content
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async def download():
                async with sdk:
                    return await sdk.download_node_content(
                        kb_id=kb_id,
                        node_id=node_id,
                        format=download_format,
                        include_metadata=include_metadata,
                        content_type=content_type
                    )
            
            content = loop.run_until_complete(download())
            
            # Prepare file response
            filename = f"node_{node_id}_{content_type}.{format_str}"
            
            # Determine MIME type
            mime_types = {
                'txt': 'text/plain',
                'json': 'application/json',
                'csv': 'text/csv',
                'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
            mime_type = mime_types.get(format_str, 'application/octet-stream')
            
            # Create file-like object
            file_obj = io.BytesIO(content)
            file_obj.seek(0)
            
            return send_file(
                file_obj,
                mimetype=mime_type,
                as_attachment=True,
                download_name=filename
            )
        finally:
            loop.close()
            
    except ValueError as e:
        return jsonify({"retcode": 102, "retmsg": str(e)}), 404
    except GraphRAGError as e:
        logger.error(f"GraphRAG error in download_node_content: {e}")
        return server_error_response(e)
    except Exception as e:
        logger.error(f"Unexpected error in download_node_content: {e}")
        return server_error_response(e)


@graphrag_bp.route('/kb/<kb_id>/statistics', methods=['GET'])
@login_required
@validate_request("kb_id")
def get_graph_statistics(kb_id: str):
    """
    Get knowledge graph statistics
    
    Args:
        kb_id: Knowledge base ID
        
    Returns:
        Graph statistics including node count, edge count, etc.
    """
    try:
        # Validate access
        kb = validate_kb_access(kb_id)
        
        # Get SDK instance
        sdk = get_sdk_instance()
        
        # Get statistics
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async def get_stats():
                async with sdk:
                    return await sdk.get_graph_statistics(kb_id, use_cache=True)
            
            stats = loop.run_until_complete(get_stats())
            
            return jsonify({
                "retcode": 0,
                "retmsg": "success",
                "data": {
                    "statistics": stats,
                    "kb_info": {
                        "id": kb.id,
                        "name": kb.name
                    }
                }
            })
        finally:
            loop.close()
            
    except ValueError as e:
        return jsonify({"retcode": 102, "retmsg": str(e)}), 404
    except GraphRAGError as e:
        logger.error(f"GraphRAG error in get_graph_statistics: {e}")
        return server_error_response(e)
    except Exception as e:
        logger.error(f"Unexpected error in get_graph_statistics: {e}")
        return server_error_response(e)


# Health check endpoint
@graphrag_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for GraphRAG API"""
    try:
        sdk = get_sdk_instance()
        return jsonify({
            "retcode": 0,
            "retmsg": "GraphRAG API is healthy",
            "data": {
                "status": "healthy",
                "version": "1.0.0",
                "sdk_initialized": sdk is not None
            }
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "retcode": 500,
            "retmsg": f"Health check failed: {e}",
            "data": {
                "status": "unhealthy"
            }
        }), 500
