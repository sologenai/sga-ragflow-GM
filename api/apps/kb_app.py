#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
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
from datetime import datetime

from flask import request
from flask_login import login_required, current_user

from api.db.services import duplicate_name
from api.db.services.document_service import DocumentService
from api.db.services.file2document_service import File2DocumentService
from api.db.services.file_service import FileService
from api.db.services.user_service import TenantService, UserTenantService
from api.utils.api_utils import server_error_response, get_data_error_result, validate_request, not_allowed_parameters
from api.utils import get_uuid
from api.db import StatusEnum, FileSource
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.db_models import File
from api.utils.api_utils import get_json_result
from api import settings
from rag.nlp import search
from api.constants import DATASET_NAME_LIMIT
from rag.settings import PAGERANK_FLD
from rag.utils.storage_factory import STORAGE_IMPL


@manager.route('/create', methods=['post'])  # noqa: F821
@login_required
@validate_request("name")
def create():
    req = request.json
    dataset_name = req["name"]
    if not isinstance(dataset_name, str):
        return get_data_error_result(message="Dataset name must be string.")
    if dataset_name.strip() == "":
        return get_data_error_result(message="Dataset name can't be empty.")
    if len(dataset_name.encode("utf-8")) > DATASET_NAME_LIMIT:
        return get_data_error_result(
            message=f"Dataset name length is {len(dataset_name)} which is larger than {DATASET_NAME_LIMIT}")

    dataset_name = dataset_name.strip()
    dataset_name = duplicate_name(
        KnowledgebaseService.query,
        name=dataset_name,
        tenant_id=current_user.id,
        status=StatusEnum.VALID.value)
    try:
        req["id"] = get_uuid()
        req["name"] = dataset_name
        req["tenant_id"] = current_user.id
        req["created_by"] = current_user.id
        e, t = TenantService.get_by_id(current_user.id)
        if not e:
            return get_data_error_result(message="Tenant not found.")
        req["embd_id"] = t.embd_id
        if not KnowledgebaseService.save(**req):
            return get_data_error_result()
        return get_json_result(data={"kb_id": req["id"]})
    except Exception as e:
        return server_error_response(e)


@manager.route('/update', methods=['post'])  # noqa: F821
@login_required
@validate_request("kb_id", "name", "description", "parser_id")
@not_allowed_parameters("id", "tenant_id", "created_by", "create_time", "update_time", "create_date", "update_date", "created_by")
def update():
    req = request.json
    if not isinstance(req["name"], str):
        return get_data_error_result(message="Dataset name must be string.")
    if req["name"].strip() == "":
        return get_data_error_result(message="Dataset name can't be empty.")
    if len(req["name"].encode("utf-8")) > DATASET_NAME_LIMIT:
        return get_data_error_result(
            message=f"Dataset name length is {len(req['name'])} which is large than {DATASET_NAME_LIMIT}")
    req["name"] = req["name"].strip()

    if not KnowledgebaseService.accessible4deletion(req["kb_id"], current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=settings.RetCode.AUTHENTICATION_ERROR
        )
    try:
        if not KnowledgebaseService.query(
                created_by=current_user.id, id=req["kb_id"]):
            return get_json_result(
                data=False, message='Only owner of knowledgebase authorized for this operation.',
                code=settings.RetCode.OPERATING_ERROR)

        e, kb = KnowledgebaseService.get_by_id(req["kb_id"])
        if not e:
            return get_data_error_result(
                message="Can't find this knowledgebase!")

        if req["name"].lower() != kb.name.lower() \
                and len(
            KnowledgebaseService.query(name=req["name"], tenant_id=current_user.id, status=StatusEnum.VALID.value)) >= 1:
            return get_data_error_result(
                message="Duplicated knowledgebase name.")

        del req["kb_id"]
        if not KnowledgebaseService.update_by_id(kb.id, req):
            return get_data_error_result()

        if kb.pagerank != req.get("pagerank", 0):
            if req.get("pagerank", 0) > 0:
                settings.docStoreConn.update({"kb_id": kb.id}, {PAGERANK_FLD: req["pagerank"]},
                                         search.index_name(kb.tenant_id), kb.id)
            else:
                # Elasticsearch requires PAGERANK_FLD be non-zero!
                settings.docStoreConn.update({"exists": PAGERANK_FLD}, {"remove": PAGERANK_FLD},
                                         search.index_name(kb.tenant_id), kb.id)

        e, kb = KnowledgebaseService.get_by_id(kb.id)
        if not e:
            return get_data_error_result(
                message="Database error (Knowledgebase rename)!")
        kb = kb.to_dict()
        kb.update(req)

        return get_json_result(data=kb)
    except Exception as e:
        return server_error_response(e)


@manager.route('/detail', methods=['GET'])  # noqa: F821
@login_required
def detail():
    kb_id = request.args["kb_id"]
    try:
        tenants = UserTenantService.query(user_id=current_user.id)
        for tenant in tenants:
            if KnowledgebaseService.query(
                    tenant_id=tenant.tenant_id, id=kb_id):
                break
        else:
            return get_json_result(
                data=False, message='Only owner of knowledgebase authorized for this operation.',
                code=settings.RetCode.OPERATING_ERROR)
        kb = KnowledgebaseService.get_detail(kb_id)
        if not kb:
            return get_data_error_result(
                message="Can't find this knowledgebase!")
        kb["size"] = DocumentService.get_total_size_by_kb_id(kb_id=kb["id"],keywords="", run_status=[], types=[])
        return get_json_result(data=kb)
    except Exception as e:
        return server_error_response(e)


@manager.route('/list', methods=['POST'])  # noqa: F821
@login_required
def list_kbs():
    keywords = request.args.get("keywords", "")
    page_number = int(request.args.get("page", 0))
    items_per_page = int(request.args.get("page_size", 0))
    parser_id = request.args.get("parser_id")
    orderby = request.args.get("orderby", "create_time")
    if request.args.get("desc", "true").lower() == "false":
        desc = False
    else:
        desc = True

    req = request.get_json()
    owner_ids = req.get("owner_ids", [])
    try:
        if not owner_ids:
            tenants = TenantService.get_joined_tenants_by_user_id(current_user.id)
            tenants = [m["tenant_id"] for m in tenants]
            kbs, total = KnowledgebaseService.get_by_tenant_ids(
                tenants, current_user.id, page_number,
                items_per_page, orderby, desc, keywords, parser_id)
        else:
            tenants = owner_ids
            kbs, total = KnowledgebaseService.get_by_tenant_ids(
                tenants, current_user.id, 0,
                0, orderby, desc, keywords, parser_id)
            kbs = [kb for kb in kbs if kb["tenant_id"] in tenants]
            total = len(kbs)
            if page_number and items_per_page:
                kbs = kbs[(page_number-1)*items_per_page:page_number*items_per_page]
        return get_json_result(data={"kbs": kbs, "total": total})
    except Exception as e:
        return server_error_response(e)

@manager.route('/rm', methods=['post'])  # noqa: F821
@login_required
@validate_request("kb_id")
def rm():
    req = request.json
    if not KnowledgebaseService.accessible4deletion(req["kb_id"], current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=settings.RetCode.AUTHENTICATION_ERROR
        )
    try:
        kbs = KnowledgebaseService.query(
            created_by=current_user.id, id=req["kb_id"])
        if not kbs:
            return get_json_result(
                data=False, message='Only owner of knowledgebase authorized for this operation.',
                code=settings.RetCode.OPERATING_ERROR)

        for doc in DocumentService.query(kb_id=req["kb_id"]):
            if not DocumentService.remove_document(doc, kbs[0].tenant_id):
                return get_data_error_result(
                    message="Database error (Document removal)!")
            f2d = File2DocumentService.get_by_document_id(doc.id)
            if f2d:
                FileService.filter_delete([File.source_type == FileSource.KNOWLEDGEBASE, File.id == f2d[0].file_id])
            File2DocumentService.delete_by_document_id(doc.id)
        FileService.filter_delete(
            [File.source_type == FileSource.KNOWLEDGEBASE, File.type == "folder", File.name == kbs[0].name])
        if not KnowledgebaseService.delete_by_id(req["kb_id"]):
            return get_data_error_result(
                message="Database error (Knowledgebase removal)!")
        for kb in kbs:
            settings.docStoreConn.delete({"kb_id": kb.id}, search.index_name(kb.tenant_id), kb.id)
            settings.docStoreConn.deleteIdx(search.index_name(kb.tenant_id), kb.id)
            if hasattr(STORAGE_IMPL, 'remove_bucket'):
                STORAGE_IMPL.remove_bucket(kb.id)
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route('/<kb_id>/tags', methods=['GET'])  # noqa: F821
@login_required
def list_tags(kb_id):
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=settings.RetCode.AUTHENTICATION_ERROR
        )

    tenants = UserTenantService.get_tenants_by_user_id(current_user.id)
    tags = []
    for tenant in tenants:
        tags += settings.retrievaler.all_tags(tenant["tenant_id"], [kb_id])
    return get_json_result(data=tags)


@manager.route('/tags', methods=['GET'])  # noqa: F821
@login_required
def list_tags_from_kbs():
    kb_ids = request.args.get("kb_ids", "").split(",")
    for kb_id in kb_ids:
        if not KnowledgebaseService.accessible(kb_id, current_user.id):
            return get_json_result(
                data=False,
                message='No authorization.',
                code=settings.RetCode.AUTHENTICATION_ERROR
            )

    tenants = UserTenantService.get_tenants_by_user_id(current_user.id)
    tags = []
    for tenant in tenants:
        tags += settings.retrievaler.all_tags(tenant["tenant_id"], kb_ids)
    return get_json_result(data=tags)


@manager.route('/<kb_id>/rm_tags', methods=['POST'])  # noqa: F821
@login_required
def rm_tags(kb_id):
    req = request.json
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=settings.RetCode.AUTHENTICATION_ERROR
        )
    e, kb = KnowledgebaseService.get_by_id(kb_id)

    for t in req["tags"]:
        settings.docStoreConn.update({"tag_kwd": t, "kb_id": [kb_id]},
                                     {"remove": {"tag_kwd": t}},
                                     search.index_name(kb.tenant_id),
                                     kb_id)
    return get_json_result(data=True)


@manager.route('/<kb_id>/rename_tag', methods=['POST'])  # noqa: F821
@login_required
def rename_tags(kb_id):
    req = request.json
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=settings.RetCode.AUTHENTICATION_ERROR
        )
    e, kb = KnowledgebaseService.get_by_id(kb_id)

    settings.docStoreConn.update({"tag_kwd": req["from_tag"], "kb_id": [kb_id]},
                                     {"remove": {"tag_kwd": req["from_tag"].strip()}, "add": {"tag_kwd": req["to_tag"]}},
                                     search.index_name(kb.tenant_id),
                                     kb_id)
    return get_json_result(data=True)


@manager.route('/<kb_id>/knowledge_graph', methods=['GET'])  # noqa: F821
@login_required
def knowledge_graph(kb_id):
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=settings.RetCode.AUTHENTICATION_ERROR
        )
    _, kb = KnowledgebaseService.get_by_id(kb_id)
    req = {
        "kb_id": [kb_id],
        "knowledge_graph_kwd": ["graph"]
    }

    obj = {"graph": {}, "mind_map": {}}
    if not settings.docStoreConn.indexExist(search.index_name(kb.tenant_id), kb_id):
        return get_json_result(data=obj)
    sres = settings.retrievaler.search(req, search.index_name(kb.tenant_id), [kb_id])
    if not len(sres.ids):
        return get_json_result(data=obj)

    for id in sres.ids[:1]:
        ty = sres.field[id]["knowledge_graph_kwd"]
        try:
            content_json = json.loads(sres.field[id]["content_with_weight"])
        except Exception:
            continue

        obj[ty] = content_json

    if "nodes" in obj["graph"]:
        obj["graph"]["nodes"] = sorted(obj["graph"]["nodes"], key=lambda x: x.get("pagerank", 0), reverse=True)[:256]
        if "edges" in obj["graph"]:
            node_id_set = { o["id"] for o in obj["graph"]["nodes"] }
            filtered_edges = [o for o in obj["graph"]["edges"] if o["source"] != o["target"] and o["source"] in node_id_set and o["target"] in node_id_set]
            obj["graph"]["edges"] = sorted(filtered_edges, key=lambda x: x.get("weight", 0), reverse=True)[:128]
    return get_json_result(data=obj)


@manager.route('/<kb_id>/knowledge_graph', methods=['DELETE'])  # noqa: F821
@login_required
def delete_knowledge_graph(kb_id):
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=settings.RetCode.AUTHENTICATION_ERROR
        )
    _, kb = KnowledgebaseService.get_by_id(kb_id)
    settings.docStoreConn.delete({"knowledge_graph_kwd": ["graph", "subgraph", "entity", "relation"]}, search.index_name(kb.tenant_id), kb_id)

    return get_json_result(data=True)


@manager.route('/<kb_id>/knowledge_graph/search', methods=['POST'])  # noqa: F821
@login_required
def search_knowledge_graph_nodes(kb_id):
    """Search nodes in knowledge graph by various criteria."""
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=settings.RetCode.AUTHENTICATION_ERROR
        )

    try:
        req = request.json
        if not req:
            return get_json_result(
                data=False,
                message='Request body is required.',
                code=settings.RetCode.ARGUMENT_ERROR
            )

        # Extract search parameters
        query = req.get('query', '').strip()
        entity_types = req.get('entity_types', [])
        limit = min(req.get('limit', 50), 200)  # Max 200 results
        offset = max(req.get('offset', 0), 0)

        if not query and not entity_types:
            return get_json_result(
                data={"nodes": [], "total": 0},
                message='Query or entity_types is required.'
            )

        _, kb = KnowledgebaseService.get_by_id(kb_id)

        # Check if knowledge graph exists
        if not settings.docStoreConn.indexExist(search.index_name(kb.tenant_id), kb_id):
            return get_json_result(data={"nodes": [], "total": 0})

        # Build search request for graph data
        search_req = {
            "kb_id": [kb_id],
            "knowledge_graph_kwd": ["graph"]
        }

        # Get the knowledge graph
        sres = settings.retrievaler.search(search_req, search.index_name(kb.tenant_id), [kb_id])
        if not len(sres.ids):
            return get_json_result(data={"nodes": [], "total": 0})

        # Parse graph data
        graph_data = None
        for id in sres.ids[:1]:
            try:
                content_json = json.loads(sres.field[id]["content_with_weight"])
                graph_data = content_json
                break
            except Exception:
                continue

        if not graph_data or "nodes" not in graph_data:
            return get_json_result(data={"nodes": [], "total": 0})

        # Filter nodes based on search criteria
        filtered_nodes = []
        query_lower = query.lower() if query else ""

        for node in graph_data["nodes"]:
            node_id = node.get("id", "").lower()
            node_description = node.get("description", "").lower()
            node_entity_type = node.get("entity_type", "").lower()

            # Check query match (in id or description)
            query_match = True
            if query:
                query_match = (query_lower in node_id or
                             query_lower in node_description)

            # Check entity type match
            type_match = True
            if entity_types:
                type_match = node_entity_type in [t.lower() for t in entity_types]

            if query_match and type_match:
                # Add additional metadata for frontend
                enhanced_node = {
                    **node,
                    "pagerank": node.get("pagerank", 0),
                    "communities": node.get("communities", []),
                    "source_id": node.get("source_id", [])
                }
                filtered_nodes.append(enhanced_node)

        # Sort by pagerank (relevance)
        filtered_nodes.sort(key=lambda x: x.get("pagerank", 0), reverse=True)

        # Apply pagination
        total = len(filtered_nodes)
        paginated_nodes = filtered_nodes[offset:offset + limit]

        return get_json_result(data={
            "nodes": paginated_nodes,
            "total": total,
            "offset": offset,
            "limit": limit
        })

    except Exception as e:
        logging.error(f"Error searching knowledge graph nodes: {e}", exc_info=True)
        return get_json_result(
            data=False,
            message=f'Search failed: {str(e)}',
            code=settings.RetCode.SERVER_ERROR
        )


@manager.route('/<kb_id>/knowledge_graph/node/<node_id>/files', methods=['GET'])  # noqa: F821
@login_required
def get_node_associated_files(kb_id, node_id):
    """Get files and text chunks associated with a specific node."""
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=settings.RetCode.AUTHENTICATION_ERROR
        )

    try:
        _, kb = KnowledgebaseService.get_by_id(kb_id)

        # Check if knowledge graph exists
        if not settings.docStoreConn.indexExist(search.index_name(kb.tenant_id), kb_id):
            return get_json_result(data={"files": [], "chunks": []})

        # First, get the node information from the graph
        graph_req = {
            "kb_id": [kb_id],
            "knowledge_graph_kwd": ["graph"]
        }

        graph_sres = settings.retrievaler.search(graph_req, search.index_name(kb.tenant_id), [kb_id])
        if not len(graph_sres.ids):
            return get_json_result(data={"files": [], "chunks": []})

        # Find the specific node and its source documents
        node_source_ids = []
        node_info = None

        for id in graph_sres.ids[:1]:
            try:
                content_json = json.loads(graph_sres.field[id]["content_with_weight"])
                if "nodes" in content_json:
                    for node in content_json["nodes"]:
                        if node.get("id") == node_id:
                            node_info = node
                            node_source_ids = node.get("source_id", [])
                            break
                if node_info:
                    break
            except Exception:
                continue

        if not node_info:
            return get_json_result(
                data={"files": [], "chunks": []},
                message=f"Node '{node_id}' not found in knowledge graph."
            )

        # Get associated chunks that mention this entity
        chunks_req = {
            "kb_id": [kb_id],
            "important_kwd": [node_id]  # Search for chunks that have this entity as important
        }

        chunks_sres = settings.retrievaler.search(
            chunks_req,
            search.index_name(kb.tenant_id),
            [kb_id],
            size=100  # Limit to 100 chunks
        )

        # Process chunks
        associated_chunks = []
        file_ids = set(node_source_ids)

        for chunk_id in chunks_sres.ids:
            try:
                chunk_data = chunks_sres.field[chunk_id]
                chunk_info = {
                    "id": chunk_id,
                    "content": chunk_data.get("content_with_weight", ""),
                    "doc_id": chunk_data.get("doc_id", ""),
                    "docnm_kwd": chunk_data.get("docnm_kwd", ""),
                    "page_num_int": chunk_data.get("page_num_int", []),
                    "important_kwd": chunk_data.get("important_kwd", []),
                    "entities_kwd": chunk_data.get("entities_kwd", [])
                }
                associated_chunks.append(chunk_info)

                # Collect file IDs from chunks
                if chunk_data.get("doc_id"):
                    file_ids.add(chunk_data.get("doc_id"))

            except Exception as e:
                logging.warning(f"Error processing chunk {chunk_id}: {e}")
                continue

        # Get file information
        associated_files = []
        if file_ids:
            try:
                # Get document information from document service
                for doc_id in file_ids:
                    try:
                        doc = DocumentService.get_by_id(doc_id)
                        if doc:
                            file_info = {
                                "id": doc.id,
                                "name": doc.name,
                                "type": doc.type,
                                "size": doc.size,
                                "chunk_num": doc.chunk_num,
                                "kb_id": doc.kb_id,
                                "created_by": doc.created_by,
                                "create_time": doc.create_time.isoformat() if doc.create_time else None,
                                "update_time": doc.update_time.isoformat() if doc.update_time else None
                            }
                            associated_files.append(file_info)
                    except Exception as e:
                        logging.warning(f"Error getting document {doc_id}: {e}")
                        continue
            except Exception as e:
                logging.warning(f"Error retrieving document information: {e}")

        return get_json_result(data={
            "node": node_info,
            "files": associated_files,
            "chunks": associated_chunks,
            "total_files": len(associated_files),
            "total_chunks": len(associated_chunks)
        })

    except Exception as e:
        logging.error(f"Error getting node associated files: {e}", exc_info=True)
        return get_json_result(
            data=False,
            message=f'Failed to get associated files: {str(e)}',
            code=settings.RetCode.SERVER_ERROR
        )


@manager.route('/<kb_id>/knowledge_graph/node/<node_id>/download', methods=['POST'])  # noqa: F821
@login_required
def download_node_content(kb_id, node_id):
    """Download content related to a specific node (chunks or files)."""
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=settings.RetCode.AUTHENTICATION_ERROR
        )

    try:
        req = request.json
        if not req:
            return get_json_result(
                data=False,
                message='Request body is required.',
                code=settings.RetCode.ARGUMENT_ERROR
            )

        download_type = req.get('type', 'chunks')  # 'chunks' or 'summary'
        format_type = req.get('format', 'txt')  # 'txt', 'json', 'csv'
        include_metadata = req.get('include_metadata', True)

        _, kb = KnowledgebaseService.get_by_id(kb_id)

        # Get node information and associated content
        if not settings.docStoreConn.indexExist(search.index_name(kb.tenant_id), kb_id):
            return get_json_result(
                data=False,
                message='Knowledge graph not found.',
                code=settings.RetCode.DATA_ERROR
            )

        # Get the node information
        graph_req = {
            "kb_id": [kb_id],
            "knowledge_graph_kwd": ["graph"]
        }

        graph_sres = settings.retrievaler.search(graph_req, search.index_name(kb.tenant_id), [kb_id])
        if not len(graph_sres.ids):
            return get_json_result(
                data=False,
                message='Knowledge graph not found.',
                code=settings.RetCode.DATA_ERROR
            )

        # Find the specific node
        node_info = None
        for id in graph_sres.ids[:1]:
            try:
                content_json = json.loads(graph_sres.field[id]["content_with_weight"])
                if "nodes" in content_json:
                    for node in content_json["nodes"]:
                        if node.get("id") == node_id:
                            node_info = node
                            break
                if node_info:
                    break
            except Exception:
                continue

        if not node_info:
            return get_json_result(
                data=False,
                message=f"Node '{node_id}' not found.",
                code=settings.RetCode.DATA_ERROR
            )

        # Get associated chunks
        chunks_req = {
            "kb_id": [kb_id],
            "important_kwd": [node_id]
        }

        chunks_sres = settings.retrievaler.search(
            chunks_req,
            search.index_name(kb.tenant_id),
            [kb_id],
            size=1000  # Get more chunks for download
        )

        # Process content based on download type
        content_data = {
            "node_id": node_id,
            "node_info": node_info,
            "generated_at": datetime.now().isoformat(),
            "kb_id": kb_id,
            "chunks": []
        }

        for chunk_id in chunks_sres.ids:
            try:
                chunk_data = chunks_sres.field[chunk_id]
                chunk_content = {
                    "id": chunk_id,
                    "content": chunk_data.get("content_with_weight", ""),
                    "doc_name": chunk_data.get("docnm_kwd", ""),
                    "page_numbers": chunk_data.get("page_num_int", []),
                }

                if include_metadata:
                    chunk_content.update({
                        "doc_id": chunk_data.get("doc_id", ""),
                        "important_keywords": chunk_data.get("important_kwd", []),
                        "entities": chunk_data.get("entities_kwd", []),
                        "weight": chunk_data.get("weight_flt", 0.0)
                    })

                content_data["chunks"].append(chunk_content)

            except Exception as e:
                continue

        # Generate downloadable content based on format
        if format_type == 'json':
            import json
            content = json.dumps(content_data, indent=2, ensure_ascii=False)
            mimetype = 'application/json'
            filename = f"node_{node_id}_content.json"

        elif format_type == 'csv':
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            headers = ['chunk_id', 'content', 'doc_name', 'page_numbers']
            if include_metadata:
                headers.extend(['doc_id', 'important_keywords', 'entities', 'weight'])
            writer.writerow(headers)

            # Write data
            for chunk in content_data["chunks"]:
                row = [
                    chunk['id'],
                    chunk['content'],
                    chunk['doc_name'],
                    ';'.join(map(str, chunk['page_numbers']))
                ]
                if include_metadata:
                    row.extend([
                        chunk.get('doc_id', ''),
                        ';'.join(chunk.get('important_keywords', [])),
                        ';'.join(chunk.get('entities', [])),
                        chunk.get('weight', 0.0)
                    ])
                writer.writerow(row)

            content = output.getvalue()
            mimetype = 'text/csv'
            filename = f"node_{node_id}_content.csv"

        else:  # txt format
            lines = [
                f"Node: {node_id}",
                f"Entity Type: {node_info.get('entity_type', 'Unknown')}",
                f"Description: {node_info.get('description', 'No description')}",
                f"PageRank: {node_info.get('pagerank', 0)}",
                f"Generated: {content_data['generated_at']}",
                f"Total Chunks: {len(content_data['chunks'])}",
                "=" * 80,
                ""
            ]

            for i, chunk in enumerate(content_data["chunks"], 1):
                lines.extend([
                    f"Chunk {i}: {chunk['id']}",
                    f"Document: {chunk['doc_name']}",
                    f"Pages: {', '.join(map(str, chunk['page_numbers']))}",
                    "-" * 40,
                    chunk['content'],
                    "",
                    "=" * 80,
                    ""
                ])

            content = '\n'.join(lines)
            mimetype = 'text/plain'
            filename = f"node_{node_id}_content.txt"

        # Return download response
        from flask import Response
        return Response(
            content,
            mimetype=mimetype,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': f'{mimetype}; charset=utf-8'
            }
        )

    except Exception as e:
        return get_json_result(
            data=False,
            message=f'Download failed: {str(e)}',
            code=settings.RetCode.SERVER_ERROR
        )


@manager.route("/get_meta", methods=["GET"])  # noqa: F821
@login_required
def get_meta():
    kb_ids = request.args.get("kb_ids", "").split(",")
    for kb_id in kb_ids:
        if not KnowledgebaseService.accessible(kb_id, current_user.id):
            return get_json_result(
                data=False,
                message='No authorization.',
                code=settings.RetCode.AUTHENTICATION_ERROR
            )
    return get_json_result(data=DocumentService.get_meta_by_kbs(kb_ids))


@manager.route("/basic_info", methods=["GET"])  # noqa: F821
@login_required
def get_basic_info():
    kb_id = request.args.get("kb_id", "")
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=settings.RetCode.AUTHENTICATION_ERROR
        )

    basic_info = DocumentService.knowledgebase_basic_info(kb_id)

    return get_json_result(data=basic_info)
