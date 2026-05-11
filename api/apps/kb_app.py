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
import hashlib
import inspect
import io
import json
import logging
import os
import random
import re
import zipfile
from datetime import datetime

from common.metadata_utils import turn2jsonschema
from quart import Response, request
import numpy as np

from api.db.services.connector_service import Connector2KbService
from api.db.services.llm_service import LLMBundle
from api.db.services.document_service import DocumentService, queue_raptor_o_graphrag_tasks
from api.db.services.doc_metadata_service import DocMetadataService
from api.db.services.file2document_service import File2DocumentService
from api.db.services.file_service import FileService
from api.db.services.pipeline_operation_log_service import PipelineOperationLogService
from api.db.services.task_service import TaskService, GRAPH_RAPTOR_FAKE_DOC_ID
from api.db.services.user_service import TenantService, UserTenantService
from api.utils.api_utils import (
    get_error_data_result,
    server_error_response,
    get_data_error_result,
    validate_request,
    not_allowed_parameters,
    get_request_json,
)
from common.misc_utils import get_uuid, thread_pool_exec
from api.db import AuditActionType, VALID_FILE_TYPES
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.audit_log_service import AuditLogService
from api.db.db_models import File
from api.utils.api_utils import get_json_result
from rag.graphrag.task_monitor import DOC_TTL, RESUME_PREFIX, GraphRAGTaskMonitor
from rag.nlp import search
from api.constants import DATASET_NAME_LIMIT
from rag.utils.redis_conn import REDIS_CONN
from common.constants import RetCode, PipelineTaskType, StatusEnum, VALID_TASK_STATUS, FileSource, LLMType, PAGERANK_FLD
from common import settings
from common.doc_store.doc_store_base import OrderByExpr
from common.doc_store.vector_mapping import vector_dims_for_index
from api.apps import login_required, current_user


def _to_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _docstore_result_window() -> int:
    return max(1, _to_int(os.environ.get("DOCSTORE_RESULT_WINDOW"), 10000))


def _bounded_docstore_page(offset: int, requested_size: int) -> int:
    remaining = _docstore_result_window() - max(offset, 0)
    if remaining <= 0:
        return 0
    return max(0, min(requested_size, remaining))


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _kg_kind_count(kb, idx_name: str, kind: str, *, active_only: bool = False) -> int:
    conditions = {
        "kb_id": kb.id,
        "knowledge_graph_kwd": [kind],
    }
    if active_only:
        conditions["removed_kwd"] = "N"
    res = settings.docStoreConn.search(
        [],
        [],
        conditions,
        [],
        OrderByExpr(),
        0,
        1,
        idx_name,
        [kb.id],
    )
    return _to_int(settings.docStoreConn.get_total(res), 0)


def _collect_source_ids_from_kg_kind(
    kb,
    idx_name: str,
    kind: str,
    *,
    wanted_doc_ids: set[str] | None = None,
    existing_doc_ids: set[str] | None = None,
    page_size: int = 512,
    max_rows: int | None = None,
) -> set[str]:
    source_ids = set(existing_doc_ids or set())
    if wanted_doc_ids and source_ids >= wanted_doc_ids:
        return source_ids

    max_rows = max_rows or _to_int(os.environ.get("GRAPHRAG_SUMMARY_SOURCE_SCAN_LIMIT"), 300000)
    fields = ["source_id"]
    for offset in range(0, max_rows, page_size):
        limit = _bounded_docstore_page(offset, page_size)
        if limit <= 0:
            break
        res = settings.docStoreConn.search(
            fields,
            [],
            {"kb_id": kb.id, "knowledge_graph_kwd": [kind]},
            [],
            OrderByExpr(),
            offset,
            limit,
            idx_name,
            [kb.id],
        )
        rows = settings.docStoreConn.get_fields(res, fields) or {}
        if not rows:
            break
        for row in rows.values():
            source_ids.update(_as_list(row.get("source_id")))
        if wanted_doc_ids and source_ids >= wanted_doc_ids:
            break
    if wanted_doc_ids and source_ids < wanted_doc_ids:
        for doc_id in sorted(wanted_doc_ids - source_ids):
            conditions = {"kb_id": kb.id, "knowledge_graph_kwd": [kind], "source_id": doc_id}
            res = settings.docStoreConn.search(
                fields,
                [],
                conditions,
                [],
                OrderByExpr(),
                0,
                1,
                idx_name,
                [kb.id],
            )
            rows = settings.docStoreConn.get_fields(res, fields) or {}
            if rows:
                source_ids.add(doc_id)
    return source_ids


def _safe_json_loads(value, default=None):
    if not isinstance(value, str) or not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _graph_summary_cache_key(kb_id: str) -> str:
    return f"graphrag:graph_summary:{kb_id}"


def _clear_graph_summary_cache(kb_id: str) -> None:
    try:
        REDIS_CONN.delete(_graph_summary_cache_key(kb_id))
    except Exception as e:
        logging.debug("Failed to clear GraphRAG summary cache for kb %s: %s", kb_id, e)


def _graph_data_exists(kb, idx_name: str) -> bool:
    if not settings.docStoreConn.index_exist(idx_name, kb.id):
        return False
    res = settings.docStoreConn.search(
        [],
        [],
        {
            "kb_id": kb.id,
            "knowledge_graph_kwd": ["graph", "subgraph", "entity", "relation", "community_report", "ty2ents"],
        },
        [],
        OrderByExpr(),
        0,
        1,
        idx_name,
        [kb.id],
    )
    return _to_int(settings.docStoreConn.get_total(res), 0) > 0


GRAPHRAG_EXPORT_VERSION = 1
GRAPHRAG_EXPORT_KINDS = (
    "graph",
    "subgraph",
    "entity",
    "relation",
    "community_report",
    "ty2ents",
)
GRAPHRAG_EXPORT_FIELDS = (
    "content_with_weight",
    "knowledge_graph_kwd",
    "kb_id",
    "source_id",
    "available_int",
    "removed_kwd",
    "important_kwd",
    "title_tks",
    "content_ltks",
    "content_sm_ltks",
    "entity_kwd",
    "entity_type_kwd",
    "from_entity_kwd",
    "to_entity_kwd",
    "weight_int",
    "docnm_kwd",
    "weight_flt",
    "entities_kwd",
    "q_128_vec",
    "q_256_vec",
    "q_384_vec",
    "q_512_vec",
    "q_768_vec",
    "q_1024_vec",
    "q_1536_vec",
    "q_2048_vec",
    "q_2560_vec",
    "q_3072_vec",
    "q_4096_vec",
    "q_6144_vec",
    "q_8192_vec",
    "q_10240_vec",
)
_VECTOR_FIELD_RE = re.compile(r"^q_(\d+)_vec$")


def _safe_document_hash(doc: dict) -> str:
    """Best-effort file content hash used only for graph package matching."""
    try:
        bucket, location = File2DocumentService.get_storage_address(doc_id=doc["id"])
        binary = settings.STORAGE_IMPL.get(bucket, location)
        if not binary:
            return ""
        return hashlib.sha256(binary).hexdigest()
    except Exception as e:
        logging.debug("Failed to hash document %s for GraphRAG export: %s", doc.get("id"), e)
        return ""


def _graph_export_document(doc: dict, *, include_hash: bool = True) -> dict:
    payload = {
        "id": doc.get("id", ""),
        "name": doc.get("name", ""),
        "size": _to_int(doc.get("size"), 0),
        "chunk_num": _to_int(doc.get("chunk_num"), 0),
        "token_num": _to_int(doc.get("token_num"), 0),
        "parser_id": doc.get("parser_id", ""),
        "type": doc.get("type", ""),
        "suffix": doc.get("suffix", ""),
        "run": doc.get("run", ""),
        "status": doc.get("status", ""),
    }
    if include_hash:
        payload["sha256"] = _safe_document_hash(doc)
    return payload


def _graph_doc_signature(doc: dict, *fields: str) -> tuple:
    values = []
    for field in fields:
        value = doc.get(field, "")
        if field == "name":
            value = str(value).strip().lower()
        elif field in {"size", "chunk_num"}:
            value = _to_int(value, 0)
        else:
            value = str(value or "").strip().lower()
        values.append(value)
    return tuple(values)


def _unique_doc_index(docs: list[dict], *fields: str) -> dict[tuple, list[dict]]:
    index = {}
    for doc in docs:
        key = _graph_doc_signature(doc, *fields)
        if not any(key):
            continue
        index.setdefault(key, []).append(doc)
    return index


def _match_graph_export_documents(source_docs: list[dict], target_docs: list[dict]) -> dict:
    target_hash = {}
    for doc in target_docs:
        sha256 = doc.get("sha256")
        if sha256:
            target_hash.setdefault(sha256, []).append(doc)
    target_name_size_parser = _unique_doc_index(target_docs, "name", "size", "parser_id", "suffix")
    target_name_size = _unique_doc_index(target_docs, "name", "size")
    target_name = _unique_doc_index(target_docs, "name")

    matched = []
    missing = []
    conflicts = []
    mapping = {}
    used_target_ids = set()

    def choose_target(src: dict):
        candidates = []
        reason = ""
        if src.get("sha256"):
            candidates = target_hash.get(src["sha256"], [])
            reason = "sha256"
        if not candidates:
            candidates = target_name_size_parser.get(
                _graph_doc_signature(src, "name", "size", "parser_id", "suffix"),
                [],
            )
            reason = "name_size_parser_suffix"
        if not candidates:
            candidates = target_name_size.get(_graph_doc_signature(src, "name", "size"), [])
            reason = "name_size"
        if not candidates:
            candidates = target_name.get(_graph_doc_signature(src, "name"), [])
            reason = "name"
        return candidates, reason

    for src in source_docs:
        candidates, reason = choose_target(src)
        candidates = [doc for doc in candidates if doc.get("id") not in used_target_ids]
        if not candidates:
            missing.append(src)
            continue
        if len(candidates) > 1:
            conflicts.append(
                {
                    "source": src,
                    "reason": reason,
                    "candidates": candidates[:10],
                    "candidate_count": len(candidates),
                }
            )
            continue
        target = candidates[0]
        mapping[src["id"]] = target["id"]
        used_target_ids.add(target["id"])
        matched.append({"source": src, "target": target, "reason": reason})

    extra = [doc for doc in target_docs if doc.get("id") not in used_target_ids]
    return {
        "mapping": mapping,
        "matched": matched,
        "missing": missing,
        "conflicts": conflicts,
        "extra": extra,
    }


def _iter_graph_export_rows(kb, idx_name: str, *, page_size: int = 512):
    fields = list(GRAPHRAG_EXPORT_FIELDS)
    for offset in range(0, 10000000, page_size):
        res = settings.docStoreConn.search(
            fields,
            [],
            {"kb_id": kb.id, "knowledge_graph_kwd": list(GRAPHRAG_EXPORT_KINDS)},
            [],
            OrderByExpr(),
            offset,
            page_size,
            idx_name,
            [kb.id],
        )
        ids = settings.docStoreConn.get_doc_ids(res) or []
        rows = settings.docStoreConn.get_fields(res, fields) or {}
        if not ids:
            break
        for row_id in ids:
            row = dict(rows.get(row_id, {}))
            if not row:
                continue
            row["id"] = row_id
            kind = row.get("knowledge_graph_kwd")
            if kind in GRAPHRAG_EXPORT_KINDS:
                yield row
        if len(ids) < page_size:
            break


def _graph_import_package_from_bytes(raw: bytes) -> tuple[dict, list[dict]]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            rows_raw = zf.read("graph_chunks.jsonl").decode("utf-8")
    except KeyError as e:
        raise ValueError(f"Invalid graph package: missing {e.args[0]}") from e
    except zipfile.BadZipFile as e:
        raise ValueError("Invalid graph package: file is not a zip archive") from e
    except Exception as e:
        raise ValueError(f"Invalid graph package: {e}") from e

    if manifest.get("package_type") != "ragflow_graphrag_export":
        raise ValueError("Invalid graph package: package_type is not ragflow_graphrag_export")
    rows = [json.loads(line) for line in rows_raw.splitlines() if line.strip()]
    return manifest, rows


async def _read_uploaded_graph_package() -> tuple[dict, list[dict]]:
    files = await request.files
    if "file" not in files:
        raise ValueError("No graph package uploaded.")
    uploaded = files["file"]
    if hasattr(uploaded, "read"):
        raw = uploaded.read()
        if inspect.isawaitable(raw):
            raw = await raw
    else:
        raw = uploaded.stream.read()
    if not raw:
        raise ValueError("Uploaded graph package is empty.")
    return _graph_import_package_from_bytes(raw)


def _graphrag_task_running(kb) -> bool:
    task_id = kb.graphrag_task_id
    if not task_id:
        return False
    ok, task = TaskService.get_by_id(task_id)
    if not ok:
        return False
    return task.progress not in [-1, 1]


def _build_graph_import_preview(kb, manifest: dict, rows: list[dict]) -> dict:
    source_docs = manifest.get("documents") or []
    target_docs_raw, _ = DocumentService.get_by_kb_id(
        kb_id=kb.id,
        page_number=0,
        items_per_page=0,
        orderby="create_time",
        desc=False,
        keywords="",
        run_status=[],
        types=[],
        suffix=[],
    )
    target_docs = [_graph_export_document(doc, include_hash=True) for doc in target_docs_raw]
    match_result = _match_graph_export_documents(source_docs, target_docs)
    idx_name = search.index_name(kb.tenant_id)
    existing_graph = _graph_data_exists(kb, idx_name)
    running_task = _graphrag_task_running(kb)

    kind_counts = {}
    vector_dims = set()
    for row in rows:
        kind = row.get("knowledge_graph_kwd") or "unknown"
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        for key in row:
            match = _VECTOR_FIELD_RE.match(key)
            if match:
                vector_dims.add(_to_int(match.group(1), 0))

    blocking_reasons = []
    try:
        engine = settings.docStoreConn.db_type()
        if engine in {"elasticsearch", "opensearch"}:
            for dim in sorted(dim for dim in vector_dims if dim > 0):
                vector_dims_for_index(engine, dim)
    except Exception as e:
        blocking_reasons.append(f"Vector dimension is not supported by current document engine: {e}")
    if running_task:
        blocking_reasons.append("GraphRAG task is currently running.")
    if not rows:
        blocking_reasons.append("Graph package does not contain graph records.")
    if not source_docs:
        blocking_reasons.append("Graph package does not contain source document manifest.")
    if match_result["missing"]:
        blocking_reasons.append("Target dataset is missing source documents.")
    if match_result["conflicts"]:
        blocking_reasons.append("Target dataset has ambiguous document matches.")

    can_import = not blocking_reasons
    return {
        "can_import": can_import,
        "blocking_reasons": blocking_reasons,
        "existing_graph": existing_graph,
        "running_task": running_task,
        "source_kb": manifest.get("source_kb", {}),
        "exported_at": manifest.get("exported_at", ""),
        "package_version": manifest.get("version"),
        "graph_record_count": len(rows),
        "graph_kind_counts": kind_counts,
        "vector_dims": sorted(dim for dim in vector_dims if dim > 0),
        "source_document_count": len(source_docs),
        "target_document_count": len(target_docs),
        "matched_document_count": len(match_result["matched"]),
        "missing_document_count": len(match_result["missing"]),
        "extra_document_count": len(match_result["extra"]),
        "conflict_count": len(match_result["conflicts"]),
        "matched_documents": match_result["matched"][:100],
        "missing_documents": match_result["missing"][:200],
        "extra_documents": match_result["extra"][:200],
        "conflicts": match_result["conflicts"][:50],
        "doc_id_mapping": match_result["mapping"],
    }


def _replace_graph_source_ids(value, doc_id_mapping: dict[str, str]):
    if isinstance(value, list):
        return [
            doc_id_mapping.get(item, item) if isinstance(item, str) else _replace_graph_source_ids(item, doc_id_mapping)
            for item in value
        ]
    if isinstance(value, dict):
        return {key: _replace_graph_source_ids(val, doc_id_mapping) for key, val in value.items()}
    if isinstance(value, str):
        return doc_id_mapping.get(value, value)
    return value


def _rewrite_graph_import_rows(rows: list[dict], kb_id: str, doc_id_mapping: dict[str, str]) -> list[dict]:
    from rag.graphrag.utils import chunk_id, graph_chunk_id

    rewritten = []
    for row in rows:
        item = dict(row)
        kind = item.get("knowledge_graph_kwd")
        if kind not in GRAPHRAG_EXPORT_KINDS:
            continue
        item["kb_id"] = kb_id
        item["source_id"] = _replace_graph_source_ids(_as_list(item.get("source_id")), doc_id_mapping)
        if item.get("content_with_weight"):
            parsed = _safe_json_loads(item.get("content_with_weight"))
            if parsed is not None:
                item["content_with_weight"] = json.dumps(
                    _replace_graph_source_ids(parsed, doc_id_mapping),
                    ensure_ascii=False,
                )

        if kind == "graph":
            item["id"] = graph_chunk_id(kb_id)
            item["removed_kwd"] = "N"
            item["available_int"] = 0
        elif kind == "subgraph":
            item["removed_kwd"] = "N"
            item["available_int"] = 0
            item["id"] = chunk_id(item)
        else:
            item["id"] = get_uuid()
            item["available_int"] = _to_int(item.get("available_int"), 0)

        if "weight_int" in item:
            item["weight_int"] = _to_int(item.get("weight_int"), 0)
        if "weight_flt" in item:
            item["weight_flt"] = _to_float(item.get("weight_flt"), 0.0)
        rewritten.append(item)
    return rewritten


def _ensure_graph_import_index(kb, idx_name: str, rows: list[dict]) -> None:
    vector_dims = sorted(
        {
            _to_int(match.group(1), 0)
            for row in rows
            for key in row
            for match in [_VECTOR_FIELD_RE.match(key)]
            if match
        }
    )
    if not vector_dims:
        vector_dims = [0]
    for dim in vector_dims:
        settings.docStoreConn.create_idx(idx_name, kb.id, dim, kb.parser_id)


def _build_large_graph_preview(kb, idx_name: str, *, max_nodes: int = 2000, max_edges: int = 4000) -> dict:
    max_nodes = max(100, min(max_nodes, 5000))
    max_edges = max(0, min(max_edges, 10000))
    entity_total = _kg_kind_count(kb, idx_name, "entity")
    relation_total = _kg_kind_count(kb, idx_name, "relation")

    entity_scan_size = _bounded_docstore_page(0, max(max_nodes * 3, max_nodes))
    node_fields = ["entity_kwd", "entity_type_kwd", "content_with_weight", "source_id"]
    if entity_scan_size > 0:
        node_res = settings.docStoreConn.search(
            node_fields,
            [],
            {"kb_id": kb.id, "knowledge_graph_kwd": ["entity"]},
            [],
            OrderByExpr(),
            0,
            entity_scan_size,
            idx_name,
            [kb.id],
        )
        node_rows = settings.docStoreConn.get_fields(node_res, node_fields) or {}
    else:
        node_rows = {}
    nodes = []
    for row in node_rows.values():
        node_id = row.get("entity_kwd")
        if not node_id:
            continue
        attrs = _safe_json_loads(row.get("content_with_weight"), {}) or {}
        nodes.append(
            {
                "id": node_id,
                "label": node_id,
                "entity_type": row.get("entity_type_kwd") or attrs.get("entity_type"),
                "description": attrs.get("description", ""),
                "source_id": _as_list(row.get("source_id") or attrs.get("source_id")),
                "pagerank": attrs.get("pagerank", 0),
                "rank": attrs.get("rank", attrs.get("pagerank", 0)),
            }
        )
    nodes = sorted(nodes, key=lambda n: _to_float(n.get("pagerank") or n.get("rank")), reverse=True)[:max_nodes]
    node_ids = {node["id"] for node in nodes}

    edges = []
    edge_fields = ["from_entity_kwd", "to_entity_kwd", "weight_int", "content_with_weight", "source_id"]
    page_size = 512
    max_relation_scan = max(max_edges * 10, page_size)
    for offset in range(0, max_relation_scan, page_size):
        if len(edges) >= max_edges:
            break
        limit = _bounded_docstore_page(offset, page_size)
        if limit <= 0:
            break
        edge_res = settings.docStoreConn.search(
            edge_fields,
            [],
            {"kb_id": kb.id, "knowledge_graph_kwd": ["relation"]},
            [],
            OrderByExpr(),
            offset,
            limit,
            idx_name,
            [kb.id],
        )
        edge_rows = settings.docStoreConn.get_fields(edge_res, edge_fields) or {}
        if not edge_rows:
            break
        for row in edge_rows.values():
            source = row.get("from_entity_kwd")
            target = row.get("to_entity_kwd")
            if not source or not target or source == target:
                continue
            if source not in node_ids or target not in node_ids:
                continue
            attrs = _safe_json_loads(row.get("content_with_weight"), {}) or {}
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "weight": _to_int(row.get("weight_int") or attrs.get("weight"), 1),
                    "description": attrs.get("description", ""),
                    "source_id": _as_list(row.get("source_id") or attrs.get("source_id")),
                }
            )
            if len(edges) >= max_edges:
                break

    return {
        "nodes": nodes,
        "edges": edges,
        "graph": {
            "preview": True,
            "preview_reason": "large_graph",
            "total_nodes": entity_total,
            "total_edges": relation_total,
            "visible_nodes": len(nodes),
            "visible_edges": len(edges),
            "max_nodes": max_nodes,
            "max_edges": max_edges,
        },
    }


def _build_graphrag_graph_summary(kb, *, cache_only: bool = False) -> dict:
    """
    Build a lightweight graph summary for UI display.

    The summary is intentionally cheap and resilient:
    1) parse one latest graph chunk to get authoritative node/edge counts
    2) count community reports, which are stored as separate chunks
    """
    summary = {
        "has_graph": False,
        "node_count": 0,
        "edge_count": 0,
        "entity_count": 0,
        "relation_count": 0,
        "community_count": 0,
        "total_document_count": 0,
        "graph_document_count": 0,
        "pending_document_count": 0,
        "can_incremental_update": False,
    }
    cache_seconds = _to_int(os.environ.get("GRAPHRAG_SUMMARY_CACHE_SECONDS"), 60)
    cache_key = _graph_summary_cache_key(kb.id)
    if cache_seconds > 0:
        try:
            cached_raw = REDIS_CONN.get(cache_key)
            if cached_raw:
                cached = json.loads(cached_raw)
                if isinstance(cached, dict):
                    return cached
        except Exception as e:
            logging.debug("Failed to load GraphRAG summary cache for kb %s: %s", kb.id, e)
    if cache_only:
        return summary

    try:
        documents, _ = DocumentService.get_by_kb_id(
            kb_id=kb.id,
            page_number=0,
            items_per_page=0,
            orderby="create_time",
            desc=False,
            keywords="",
            run_status=[],
            types=[],
            suffix=[],
        )
        document_ids = {document["id"] for document in documents}
        summary["total_document_count"] = len(document_ids)

        idx_name = search.index_name(kb.tenant_id)
        if not settings.docStoreConn.index_exist(idx_name, kb.id):
            summary["pending_document_count"] = summary["total_document_count"]
            return summary

        # Entity/relation chunks may not carry removed_kwd and can be duplicated
        # across graph updates. The graph JSON below is the authoritative source
        # for active entity/relation totals; these counts are only a fallback.
        summary["entity_count"] = _kg_kind_count(kb, idx_name, "entity")
        summary["relation_count"] = _kg_kind_count(kb, idx_name, "relation")
        summary["community_count"] = _kg_kind_count(kb, idx_name, "community_report")

        graph_res = settings.docStoreConn.search(
            ["content_with_weight", "source_id"],
            [],
            {
                "kb_id": kb.id,
                "knowledge_graph_kwd": ["graph"],
                "removed_kwd": "N",
            },
            [],
            OrderByExpr(),
            0,
            1,
            idx_name,
            [kb.id],
        )
        graph_doc_ids = set()
        if _to_int(settings.docStoreConn.get_total(graph_res), 0) > 0:
            ids = settings.docStoreConn.get_doc_ids(graph_res) or []
            fields = settings.docStoreConn.get_fields(
                graph_res, ["content_with_weight", "source_id"]
            ) or {}
            if ids:
                graph_fields = fields.get(ids[0], {})
                graph_doc_ids.update(graph_fields.get("source_id") or [])
                graph_raw = graph_fields.get("content_with_weight")
                if isinstance(graph_raw, str) and graph_raw:
                    try:
                        graph_obj = json.loads(graph_raw)
                        if isinstance(graph_obj, dict):
                            summary["node_count"] = len(graph_obj.get("nodes") or [])
                            summary["edge_count"] = len(graph_obj.get("edges") or [])
                            graph_doc_ids.update(graph_obj.get("graph", {}).get("source_id") or [])
                    except Exception as parse_error:
                        logging.warning(
                            "Failed to parse graph chunk for kb %s: %s",
                            kb.id,
                            parse_error,
                        )

        if summary["node_count"] <= 0 and summary["entity_count"] > 0:
            summary["node_count"] = summary["entity_count"]
        if summary["edge_count"] <= 0 and summary["relation_count"] > 0:
            summary["edge_count"] = summary["relation_count"]
        if summary["node_count"] > 0:
            summary["entity_count"] = summary["node_count"]
        if summary["edge_count"] > 0:
            summary["relation_count"] = summary["edge_count"]

        summary["has_graph"] = bool(
            summary["node_count"] > 0
            or summary["edge_count"] > 0
            or summary["entity_count"] > 0
            or summary["relation_count"] > 0
            or summary["community_count"] > 0
        )
        if document_ids and len(graph_doc_ids.intersection(document_ids)) < len(document_ids) and summary["has_graph"]:
            for kind in ("entity", "relation"):
                graph_doc_ids = _collect_source_ids_from_kg_kind(
                    kb,
                    idx_name,
                    kind,
                    wanted_doc_ids=document_ids,
                    existing_doc_ids=graph_doc_ids,
                )
                if graph_doc_ids >= document_ids:
                    break

        summary["graph_document_count"] = len(graph_doc_ids.intersection(document_ids)) if document_ids else len(graph_doc_ids)
        summary["pending_document_count"] = max(summary["total_document_count"] - summary["graph_document_count"], 0)
        summary["can_incremental_update"] = bool(summary["has_graph"] and summary["pending_document_count"] > 0)
    except Exception as e:
        logging.warning("Failed to build GraphRAG summary for kb %s: %s", kb.id, e)

    if cache_seconds > 0:
        try:
            REDIS_CONN.set(cache_key, json.dumps(summary, ensure_ascii=False), cache_seconds)
        except Exception as e:
            logging.debug("Failed to store GraphRAG summary cache for kb %s: %s", kb.id, e)

    return summary


@manager.route('/create', methods=['post'])  # noqa: F821
@login_required
@validate_request("name")
async def create():
    req = await get_request_json()
    e, res = KnowledgebaseService.create_with_name(
        name = req.pop("name", None),
        tenant_id = current_user.id,
        parser_id = req.pop("parser_id", None),
        **req
    )

    if not e:
        return res

    try:
        if not KnowledgebaseService.save(**res):
            return get_data_error_result()
        ip_address = request.headers.get("X-Forwarded-For", request.headers.get("X-Real-Ip", request.remote_addr))
        if ip_address and "," in ip_address:
            ip_address = ip_address.split(",")[0].strip()
        user_agent = request.headers.get("User-Agent", "")
        try:
            AuditLogService.log(
                action_type=AuditActionType.KB_CREATED,
                user_id=current_user.id,
                user_email=current_user.email,
                resource_type="knowledgebase",
                resource_id=res["id"],
                detail={"name": res.get("name", "")},
                ip_address=ip_address,
                user_agent=user_agent,
                client_info={"path": request.path},
            )
        except Exception as audit_error:
            logging.exception(f"Failed to write kb create audit log: {audit_error}")
        return get_json_result(data={"kb_id":res["id"]})
    except Exception as e:
        return server_error_response(e)


@manager.route('/update', methods=['post'])  # noqa: F821
@login_required
@validate_request("kb_id", "name", "description", "parser_id")
@not_allowed_parameters("id", "tenant_id", "created_by", "create_time", "update_time", "create_date", "update_date", "created_by")
async def update():
    req = await get_request_json()
    if not isinstance(req["name"], str):
        return get_data_error_result(message="Dataset name must be string.")
    if req["name"].strip() == "":
        return get_data_error_result(message="Dataset name can't be empty.")
    if len(req["name"].encode("utf-8")) > DATASET_NAME_LIMIT:
        return get_data_error_result(
            message=f"Dataset name length is {len(req['name'])} which is large than {DATASET_NAME_LIMIT}")
    req["name"] = req["name"].strip()
    if settings.DOC_ENGINE_INFINITY:
        parser_id = req.get("parser_id")
        if isinstance(parser_id, str) and parser_id.lower() == "tag":
            return get_json_result(
                code=RetCode.OPERATING_ERROR,
                message="The chunking method Tag has not been supported by Infinity yet.",
                data=False,
            )
        if "pagerank" in req and req["pagerank"] > 0:
            return get_json_result(
                code=RetCode.DATA_ERROR,
                message="'pagerank' can only be set when doc_engine is elasticsearch",
                data=False,
            )

    if "kb_label" in req:
        is_valid_label, normalized_label = KnowledgebaseService.validate_kb_label(
            req.get("kb_label")
        )
        if not is_valid_label:
            return get_data_error_result(
                message="Invalid kb_label. Allowed values: manual, chat_graph, news_sync, archive_sync, or empty."
            )
        req["kb_label"] = normalized_label

    if not KnowledgebaseService.accessible4deletion(req["kb_id"], current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=RetCode.AUTHENTICATION_ERROR
        )
    try:
        # Superuser can update any knowledgebase
        if not current_user.is_superuser:
            if not KnowledgebaseService.query(
                    created_by=current_user.id, id=req["kb_id"]):
                return get_json_result(
                    data=False, message='Only owner of dataset authorized for this operation.',
                    code=RetCode.OPERATING_ERROR)

        e, kb = KnowledgebaseService.get_by_id(req["kb_id"])

        # Rename folder in FileService
        if e and req["name"].lower() != kb.name.lower():
            FileService.filter_update(
                [
                    File.tenant_id == kb.tenant_id,
                    File.source_type == FileSource.KNOWLEDGEBASE,
                    File.type == "folder",
                    File.name == kb.name,
                ],
                {"name": req["name"]},
            )

        if not e:
            return get_data_error_result(
                message="Can't find this dataset!")

        if req["name"].lower() != kb.name.lower() \
                and len(
            KnowledgebaseService.query(name=req["name"], tenant_id=current_user.id, status=StatusEnum.VALID.value)) >= 1:
            return get_data_error_result(
                message="Duplicated dataset name.")

        del req["kb_id"]
        connectors = []
        if "connectors" in req:
            connectors = req["connectors"]
            del req["connectors"]
        if not KnowledgebaseService.update_by_id(kb.id, req):
            return get_data_error_result()

        if kb.pagerank != req.get("pagerank", 0):
            if req.get("pagerank", 0) > 0:
                await thread_pool_exec(
                    settings.docStoreConn.update,
                    {"kb_id": kb.id},
                    {PAGERANK_FLD: req["pagerank"]},
                    search.index_name(kb.tenant_id),
                    kb.id,
                )
            else:
                # Elasticsearch requires PAGERANK_FLD be non-zero!
                await thread_pool_exec(
                    settings.docStoreConn.update,
                    {"exists": PAGERANK_FLD},
                    {"remove": PAGERANK_FLD},
                    search.index_name(kb.tenant_id),
                    kb.id,
                )

        e, kb = KnowledgebaseService.get_by_id(kb.id)
        if not e:
            return get_data_error_result(
                message="Database error (Knowledgebase rename)!")
        errors = Connector2KbService.link_connectors(kb.id, [conn for conn in connectors], current_user.id)
        if errors:
            logging.error("Link KB errors: ", errors)
        kb = kb.to_dict()
        kb.update(req)
        kb["connectors"] = connectors

        return get_json_result(data=kb)
    except Exception as e:
        return server_error_response(e)


@manager.route('/update_metadata_setting', methods=['post'])  # noqa: F821
@login_required
@validate_request("kb_id", "metadata")
async def update_metadata_setting():
    req = await get_request_json()
    e, kb = KnowledgebaseService.get_by_id(req["kb_id"])
    if not e:
        return get_data_error_result(
            message="Database error (Knowledgebase rename)!")
    kb = kb.to_dict()
    kb["parser_config"]["metadata"] = req["metadata"]
    kb["parser_config"]["enable_metadata"] = req.get("enable_metadata", True)
    KnowledgebaseService.update_by_id(kb["id"], kb)
    return get_json_result(data=kb)


@manager.route('/detail', methods=['GET'])  # noqa: F821
@login_required
def detail():
    kb_id = request.args["kb_id"]
    try:
        # Superuser can access any knowledgebase
        if not current_user.is_superuser:
            tenants = UserTenantService.query(user_id=current_user.id)
            for tenant in tenants:
                if KnowledgebaseService.query(
                        tenant_id=tenant.tenant_id, id=kb_id):
                    break
            else:
                return get_json_result(
                    data=False, message='Only owner of dataset authorized for this operation.',
                    code=RetCode.OPERATING_ERROR)
        kb = KnowledgebaseService.get_detail(kb_id)
        if not kb:
            return get_data_error_result(
                message="Can't find this dataset!")
        kb["size"] = DocumentService.get_total_size_by_kb_id(kb_id=kb["id"],keywords="", run_status=[], types=[])
        kb["connectors"] = Connector2KbService.list_connectors(kb_id)
        if kb["parser_config"].get("metadata"):
            kb["parser_config"]["metadata"] = turn2jsonschema(kb["parser_config"]["metadata"])

        for key in ["graphrag_task_finish_at", "raptor_task_finish_at", "mindmap_task_finish_at"]:
            if finish_at := kb.get(key):
                kb[key] = finish_at.strftime("%Y-%m-%d %H:%M:%S")
        return get_json_result(data=kb)
    except Exception as e:
        return server_error_response(e)


@manager.route('/list', methods=['POST'])  # noqa: F821
@login_required
async def list_kbs():
    args = request.args
    keywords = args.get("keywords", "")
    page_number = int(args.get("page", 0))
    items_per_page = int(args.get("page_size", 0))
    parser_id = args.get("parser_id")
    orderby = args.get("orderby", "create_time")
    if args.get("desc", "true").lower() == "false":
        desc = False
    else:
        desc = True

    req = await get_request_json()
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
async def rm():
    req = await get_request_json()
    uid = current_user.id
    user_email = current_user.email
    ip_address = request.headers.get("X-Forwarded-For", request.headers.get("X-Real-Ip", request.remote_addr))
    if ip_address and "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()
    user_agent = request.headers.get("User-Agent", "")
    if not KnowledgebaseService.accessible4deletion(req["kb_id"], uid):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=RetCode.AUTHENTICATION_ERROR
        )
    try:
        # Superuser can delete any knowledgebase
        if current_user.is_superuser:
            kbs = KnowledgebaseService.query(id=req["kb_id"])
        else:
            kbs = KnowledgebaseService.query(
                created_by=uid, id=req["kb_id"])
        if not kbs:
            return get_json_result(
                data=False, message='Only owner of dataset authorized for this operation.',
                code=RetCode.OPERATING_ERROR)

        def _rm_sync():
            for doc in DocumentService.query(kb_id=req["kb_id"]):
                if not DocumentService.remove_document(doc, kbs[0].tenant_id):
                    return get_data_error_result(
                        message="Database error (Document removal)!")
                f2d = File2DocumentService.get_by_document_id(doc.id)
                if f2d:
                    FileService.filter_delete([File.source_type == FileSource.KNOWLEDGEBASE, File.id == f2d[0].file_id])
                File2DocumentService.delete_by_document_id(doc.id)
            FileService.filter_delete(
                [
                    File.tenant_id == kbs[0].tenant_id,
                    File.source_type == FileSource.KNOWLEDGEBASE,
                    File.type == "folder",
                    File.name == kbs[0].name,
                ]
            )
            # Delete the table BEFORE deleting the database record
            for kb in kbs:
                try:
                    settings.docStoreConn.delete({"kb_id": kb.id}, search.index_name(kb.tenant_id), kb.id)
                    settings.docStoreConn.delete_idx(search.index_name(kb.tenant_id), kb.id)
                    logging.info(f"Dropped index for dataset {kb.id}")
                except Exception as e:
                    logging.error(f"Failed to drop index for dataset {kb.id}: {e}")

            if not KnowledgebaseService.delete_by_id(req["kb_id"]):
                return get_data_error_result(
                    message="Database error (Knowledgebase removal)!")
            for kb in kbs:
                if hasattr(settings.STORAGE_IMPL, 'remove_bucket'):
                    settings.STORAGE_IMPL.remove_bucket(kb.id)
            try:
                AuditLogService.log(
                    action_type=AuditActionType.KB_DELETED,
                    user_id=uid,
                    user_email=user_email,
                    resource_type="knowledgebase",
                    resource_id=req["kb_id"],
                    detail={"name": kbs[0].name if kbs else ""},
                    ip_address=ip_address,
                    user_agent=user_agent,
                    client_info={"path": request.path},
                )
            except Exception as audit_error:
                logging.exception(f"Failed to write kb delete audit log: {audit_error}")
            return get_json_result(data=True)

        return await thread_pool_exec(_rm_sync)
    except Exception as e:
        return server_error_response(e)


@manager.route('/<kb_id>/tags', methods=['GET'])  # noqa: F821
@login_required
def list_tags(kb_id):
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=RetCode.AUTHENTICATION_ERROR
        )

    tenants = UserTenantService.get_tenants_by_user_id(current_user.id)
    tags = []
    for tenant in tenants:
        tags += settings.retriever.all_tags(tenant["tenant_id"], [kb_id])
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
                code=RetCode.AUTHENTICATION_ERROR
            )

    tenants = UserTenantService.get_tenants_by_user_id(current_user.id)
    tags = []
    for tenant in tenants:
        tags += settings.retriever.all_tags(tenant["tenant_id"], kb_ids)
    return get_json_result(data=tags)


@manager.route('/<kb_id>/rm_tags', methods=['POST'])  # noqa: F821
@login_required
async def rm_tags(kb_id):
    req = await get_request_json()
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=RetCode.AUTHENTICATION_ERROR
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
async def rename_tags(kb_id):
    req = await get_request_json()
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=RetCode.AUTHENTICATION_ERROR
        )
    e, kb = KnowledgebaseService.get_by_id(kb_id)

    settings.docStoreConn.update({"tag_kwd": req["from_tag"], "kb_id": [kb_id]},
                                     {"remove": {"tag_kwd": req["from_tag"].strip()}, "add": {"tag_kwd": req["to_tag"]}},
                                     search.index_name(kb.tenant_id),
                                     kb_id)
    return get_json_result(data=True)


@manager.route('/<kb_id>/knowledge_graph', methods=['GET'])  # noqa: F821
@login_required
async def knowledge_graph(kb_id):
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=RetCode.AUTHENTICATION_ERROR
        )
    _, kb = KnowledgebaseService.get_by_id(kb_id)
    idx_name = search.index_name(kb.tenant_id)
    req = {
        "kb_id": [kb_id],
        "knowledge_graph_kwd": ["graph"]
    }

    obj = {"graph": {}, "mind_map": {}}
    if not settings.docStoreConn.index_exist(idx_name, kb_id):
        return get_json_result(data=obj)

    if request.args.get("exists_only") in {"1", "true", "True"}:
        if _graph_data_exists(kb, idx_name):
            obj["graph"] = {"graph": {"has_graph": True, "exists_only": True}}
        return get_json_result(data=obj)

    max_nodes_threshold = _to_int(request.args.get("max_nodes"), 2000)
    max_edges_threshold = _to_int(request.args.get("max_edges"), 4000)
    entity_count = _kg_kind_count(kb, idx_name, "entity")
    relation_count = _kg_kind_count(kb, idx_name, "relation")
    if entity_count > max_nodes_threshold or relation_count > max_edges_threshold:
        obj["graph"] = _build_large_graph_preview(
            kb,
            idx_name,
            max_nodes=max_nodes_threshold,
            max_edges=max_edges_threshold,
        )
        return get_json_result(data=obj)

    sres = await settings.retriever.search(req, idx_name, [kb_id])
    if not len(sres.ids):
        if entity_count > 0 or relation_count > 0:
            obj["graph"] = _build_large_graph_preview(
                kb,
                idx_name,
                max_nodes=max_nodes_threshold,
                max_edges=max_edges_threshold,
            )
        return get_json_result(data=obj)

    for id in sres.ids[:1]:
        ty = sres.field[id]["knowledge_graph_kwd"]
        try:
            content_json = json.loads(sres.field[id]["content_with_weight"])
        except Exception:
            continue

        obj[ty] = content_json

    if "nodes" in obj["graph"]:
        nodes = sorted(obj["graph"]["nodes"], key=lambda x: x.get("pagerank", 0), reverse=True)

        if len(nodes) > max_nodes_threshold:
            total_nodes = len(nodes)
            total_edges = len(obj["graph"].get("edges") or [])
            obj["graph"]["nodes"] = nodes[:max_nodes_threshold]
            node_id_set = {o["id"] for o in obj["graph"]["nodes"]}
            if "edges" in obj["graph"]:
                filtered_edges = [
                    o for o in obj["graph"]["edges"]
                    if o["source"] != o["target"] and o["source"] in node_id_set and o["target"] in node_id_set
                ]
                obj["graph"]["edges"] = sorted(filtered_edges, key=lambda x: x.get("weight", 0), reverse=True)[:max_edges_threshold]
            obj["graph"].setdefault("graph", {})
            obj["graph"]["graph"].update(
                {
                    "preview": True,
                    "preview_reason": "large_graph_snapshot",
                    "total_nodes": total_nodes,
                    "total_edges": total_edges,
                    "visible_nodes": len(obj["graph"].get("nodes") or []),
                    "visible_edges": len(obj["graph"].get("edges") or []),
                    "max_nodes": max_nodes_threshold,
                    "max_edges": max_edges_threshold,
                }
            )
        else:
            obj["graph"]["nodes"] = nodes
            if "edges" in obj["graph"]:
                node_id_set = {o["id"] for o in obj["graph"]["nodes"]}
                filtered_edges = [
                    o for o in obj["graph"]["edges"]
                    if o["source"] != o["target"] and o["source"] in node_id_set and o["target"] in node_id_set
                ]
                obj["graph"]["edges"] = sorted(filtered_edges, key=lambda x: x.get("weight", 0), reverse=True)
    return get_json_result(data=obj)


@manager.route('/<kb_id>/knowledge_graph', methods=['DELETE'])  # noqa: F821
@login_required
def delete_knowledge_graph(kb_id):
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=RetCode.AUTHENTICATION_ERROR
        )
    _, kb = KnowledgebaseService.get_by_id(kb_id)
    settings.docStoreConn.delete({"knowledge_graph_kwd": ["graph", "subgraph", "entity", "relation", "community_report", "ty2ents"]}, search.index_name(kb.tenant_id), kb_id)
    _clear_graph_summary_cache(kb_id)

    return get_json_result(data=True)


@manager.route('/<kb_id>/knowledge_graph/export', methods=['GET'])  # noqa: F821
@login_required
def export_knowledge_graph(kb_id):
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=RetCode.AUTHENTICATION_ERROR
        )
    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_data_error_result(message="Invalid Knowledgebase ID")

    idx_name = search.index_name(kb.tenant_id)
    if not _graph_data_exists(kb, idx_name):
        return get_data_error_result(message="No knowledge graph data to export.")

    documents, _ = DocumentService.get_by_kb_id(
        kb_id=kb_id,
        page_number=0,
        items_per_page=0,
        orderby="create_time",
        desc=False,
        keywords="",
        run_status=[],
        types=[],
        suffix=[],
    )
    rows = list(_iter_graph_export_rows(kb, idx_name))
    if not rows:
        return get_data_error_result(message="No knowledge graph records found.")

    kind_counts = {}
    for row in rows:
        kind = row.get("knowledge_graph_kwd") or "unknown"
        kind_counts[kind] = kind_counts.get(kind, 0) + 1

    manifest = {
        "package_type": "ragflow_graphrag_export",
        "version": GRAPHRAG_EXPORT_VERSION,
        "exported_at": datetime.now().isoformat(),
        "source_kb": {
            "id": kb.id,
            "name": kb.name,
            "tenant_id": kb.tenant_id,
            "parser_id": kb.parser_id,
            "embd_id": kb.embd_id,
            "doc_num": kb.doc_num,
            "chunk_num": kb.chunk_num,
        },
        "documents": [_graph_export_document(doc, include_hash=True) for doc in documents],
        "graph_record_count": len(rows),
        "graph_kind_counts": kind_counts,
    }

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr(
            "graph_chunks.jsonl",
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows),
        )

    filename = f"ragflow-graphrag-{kb_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
    return Response(
        output.getvalue(),
        mimetype="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/zip",
        },
    )


@manager.route('/<kb_id>/knowledge_graph/import/preview', methods=['POST'])  # noqa: F821
@login_required
async def preview_import_knowledge_graph(kb_id):
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=RetCode.AUTHENTICATION_ERROR
        )
    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_data_error_result(message="Invalid Knowledgebase ID")
    try:
        manifest, rows = await _read_uploaded_graph_package()
        preview = _build_graph_import_preview(kb, manifest, rows)
        return get_json_result(data=preview)
    except ValueError as e:
        return get_data_error_result(message=str(e))
    except Exception as e:
        logging.exception("Failed to preview GraphRAG import for kb %s", kb_id)
        return server_error_response(e)


@manager.route('/<kb_id>/knowledge_graph/import', methods=['POST'])  # noqa: F821
@login_required
async def import_knowledge_graph(kb_id):
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=RetCode.AUTHENTICATION_ERROR
        )
    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_data_error_result(message="Invalid Knowledgebase ID")

    try:
        form = await request.form
        overwrite = str(form.get("overwrite", "")).lower() in {"1", "true", "yes", "y"}
        manifest, rows = await _read_uploaded_graph_package()
        preview = _build_graph_import_preview(kb, manifest, rows)
        if preview["running_task"]:
            return get_data_error_result(message="GraphRAG task is currently running. Stop or wait for it before importing.")
        if preview["existing_graph"] and not overwrite:
            return get_json_result(
                data=preview,
                message="Target knowledge graph already exists. Set overwrite=true to replace it.",
                code=RetCode.DATA_ERROR,
            )
        if not preview["can_import"]:
            return get_json_result(
                data=preview,
                message="Graph import precheck failed. Fix missing or conflicting files before importing.",
                code=RetCode.DATA_ERROR,
            )

        idx_name = search.index_name(kb.tenant_id)
        rewritten_rows = _rewrite_graph_import_rows(rows, kb_id, preview["doc_id_mapping"])
        _ensure_graph_import_index(kb, idx_name, rewritten_rows)

        if preview["existing_graph"] and overwrite:
            settings.docStoreConn.delete(
                {"knowledge_graph_kwd": list(GRAPHRAG_EXPORT_KINDS)},
                idx_name,
                kb_id,
            )

        batch_size = _to_int(os.environ.get("GRAPHRAG_IMPORT_BATCH_SIZE"), 128)
        inserted = 0
        for start in range(0, len(rewritten_rows), batch_size):
            batch = rewritten_rows[start:start + batch_size]
            errors = settings.docStoreConn.insert(batch, idx_name, kb_id)
            if errors:
                raise RuntimeError(f"Insert graph import batch failed: {errors[:5]}")
            inserted += len(batch)

        _clear_graph_summary_cache(kb_id)
        KnowledgebaseService.update_by_id(
            kb.id,
            {
                "graphrag_task_id": None,
                "graphrag_task_finish_at": datetime.now(),
            },
        )
        return get_json_result(
            data={
                "inserted": inserted,
                "matched_document_count": preview["matched_document_count"],
                "extra_document_count": preview["extra_document_count"],
                "graph_kind_counts": preview["graph_kind_counts"],
            }
        )
    except ValueError as e:
        return get_data_error_result(message=str(e))
    except Exception as e:
        logging.exception("Failed to import GraphRAG package for kb %s", kb_id)
        return server_error_response(e)


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
                code=RetCode.AUTHENTICATION_ERROR
            )
    return get_json_result(data=DocMetadataService.get_flatted_meta_by_kbs(kb_ids))


@manager.route("/basic_info", methods=["GET"])  # noqa: F821
@login_required
def get_basic_info():
    kb_id = request.args.get("kb_id", "")
    if not KnowledgebaseService.accessible(kb_id, current_user.id):
        return get_json_result(
            data=False,
            message='No authorization.',
            code=RetCode.AUTHENTICATION_ERROR
        )

    basic_info = DocumentService.knowledgebase_basic_info(kb_id)

    return get_json_result(data=basic_info)


@manager.route("/list_pipeline_logs", methods=["POST"])  # noqa: F821
@login_required
async def list_pipeline_logs():
    kb_id = request.args.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)

    keywords = request.args.get("keywords", "")

    page_number = int(request.args.get("page", 0))
    items_per_page = int(request.args.get("page_size", 0))
    orderby = request.args.get("orderby", "create_time")
    if request.args.get("desc", "true").lower() == "false":
        desc = False
    else:
        desc = True
    create_date_from = request.args.get("create_date_from", "")
    create_date_to = request.args.get("create_date_to", "")
    if create_date_to > create_date_from:
        return get_data_error_result(message="Create data filter is abnormal.")

    req = await get_request_json()

    operation_status = req.get("operation_status", [])
    if operation_status:
        invalid_status = {s for s in operation_status if s not in VALID_TASK_STATUS}
        if invalid_status:
            return get_data_error_result(message=f"Invalid filter operation_status status conditions: {', '.join(invalid_status)}")

    types = req.get("types", [])
    if types:
        invalid_types = {t for t in types if t not in VALID_FILE_TYPES}
        if invalid_types:
            return get_data_error_result(message=f"Invalid filter conditions: {', '.join(invalid_types)} type{'s' if len(invalid_types) > 1 else ''}")

    suffix = req.get("suffix", [])

    try:
        logs, tol = PipelineOperationLogService.get_file_logs_by_kb_id(kb_id, page_number, items_per_page, orderby, desc, keywords, operation_status, types, suffix, create_date_from, create_date_to)
        return get_json_result(data={"total": tol, "logs": logs})
    except Exception as e:
        return server_error_response(e)


@manager.route("/list_pipeline_dataset_logs", methods=["POST"])  # noqa: F821
@login_required
async def list_pipeline_dataset_logs():
    kb_id = request.args.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)

    page_number = int(request.args.get("page", 0))
    items_per_page = int(request.args.get("page_size", 0))
    orderby = request.args.get("orderby", "create_time")
    if request.args.get("desc", "true").lower() == "false":
        desc = False
    else:
        desc = True
    create_date_from = request.args.get("create_date_from", "")
    create_date_to = request.args.get("create_date_to", "")
    if create_date_to > create_date_from:
        return get_data_error_result(message="Create data filter is abnormal.")

    req = await get_request_json()

    operation_status = req.get("operation_status", [])
    if operation_status:
        invalid_status = {s for s in operation_status if s not in VALID_TASK_STATUS}
        if invalid_status:
            return get_data_error_result(message=f"Invalid filter operation_status status conditions: {', '.join(invalid_status)}")

    try:
        logs, tol = PipelineOperationLogService.get_dataset_logs_by_kb_id(kb_id, page_number, items_per_page, orderby, desc, operation_status, create_date_from, create_date_to)
        return get_json_result(data={"total": tol, "logs": logs})
    except Exception as e:
        return server_error_response(e)


@manager.route("/delete_pipeline_logs", methods=["POST"])  # noqa: F821
@login_required
async def delete_pipeline_logs():
    kb_id = request.args.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)

    req = await get_request_json()
    log_ids = req.get("log_ids", [])

    PipelineOperationLogService.delete_by_ids(log_ids)

    return get_json_result(data=True)


@manager.route("/pipeline_log_detail", methods=["GET"])  # noqa: F821
@login_required
def pipeline_log_detail():
    log_id = request.args.get("log_id")
    if not log_id:
        return get_json_result(data=False, message='Lack of "Pipeline log ID"', code=RetCode.ARGUMENT_ERROR)

    ok, log = PipelineOperationLogService.get_by_id(log_id)
    if not ok:
        return get_data_error_result(message="Invalid pipeline log ID")

    return get_json_result(data=log.to_dict())


@manager.route("/run_graphrag", methods=["POST"])  # noqa: F821
@login_required
async def run_graphrag():
    req = await get_request_json()

    kb_id = req.get("kb_id", "")
    resume = bool(req.get("resume", False))
    raw_mode = str(req.get("mode") or req.get("run_mode") or "").strip()
    if raw_mode in {"generate", "full"}:
        raw_mode = "regenerate"
    elif raw_mode == "resume":
        raw_mode = ""
    if raw_mode and raw_mode not in {"incremental", "resume_failed", "regenerate"}:
        return get_error_data_result(message="Invalid GraphRAG mode. Use incremental, resume_failed, or regenerate.")
    if not kb_id:
        return get_error_data_result(message='Lack of "KB ID"')

    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_error_data_result(message="Invalid Knowledgebase ID")

    task_id = kb.graphrag_task_id
    task = None
    resume_from_task_id = ""
    if task_id:
        ok, task = TaskService.get_by_id(task_id)
        if not ok:
            logging.warning(f"A valid GraphRAG task id is expected for kb {kb_id}")
            if resume or raw_mode == "resume_failed":
                return get_error_data_result(message=f"Cannot resume GraphRAG task {task_id} for kb {kb_id}.")

        if task and task.progress not in [-1, 1]:
            return get_error_data_result(message=f"Task {task_id} in progress with status {task.progress}. A Graph Task is already running.")
    elif resume or raw_mode == "resume_failed":
        return get_error_data_result(message=f"No previous GraphRAG task found for kb {kb_id}.")

    run_mode = raw_mode
    if not run_mode:
        if resume:
            run_mode = "resume_failed" if task and task.progress == -1 else "incremental"
        else:
            run_mode = "regenerate"

    if run_mode == "resume_failed":
        if not task:
            return get_error_data_result(message=f"No previous GraphRAG task found for kb {kb_id}.")
        if task.progress != -1:
            return get_error_data_result(message="No interrupted GraphRAG task to resume. Use incremental or regenerate.")
        resume_from_task_id = task_id
    elif run_mode == "incremental":
        if task and task.progress == -1:
            return get_error_data_result(message="Previous GraphRAG task failed. Use resume_failed or regenerate before incremental update.")

    documents, _ = DocumentService.get_by_kb_id(
        kb_id=kb_id,
        page_number=0,
        items_per_page=0,
        orderby="create_time",
        desc=False,
        keywords="",
        run_status=[],
        types=[],
        suffix=[],
    )
    if not documents:
        return get_error_data_result(message=f"No documents in Knowledgebase {kb_id}")

    sample_document = documents[0]
    document_ids = [document["id"] for document in documents]
    idx_name = search.index_name(kb.tenant_id)

    if run_mode == "regenerate":
        confirm_regenerate = bool(req.get("confirm_regenerate") or req.get("confirmRegenerate"))
        if _graph_data_exists(kb, idx_name) and not confirm_regenerate:
            return get_error_data_result(
                message="Knowledge graph already exists. Regenerate requires confirm_regenerate=true. "
                "Use incremental or resume_failed unless you intentionally want to delete and rebuild."
            )
        try:
            deleted = settings.docStoreConn.delete(
                {"knowledge_graph_kwd": ["graph", "subgraph", "entity", "relation", "community_report", "ty2ents"]},
                idx_name, kb_id,
            )
            logging.info(f"Cleared {deleted} old graph records for kb {kb_id}")
            _clear_graph_summary_cache(kb_id)
        except Exception as e:
            logging.warning(f"Failed to clear old graph data for kb {kb_id}: {e}")

    task_id = queue_raptor_o_graphrag_tasks(sample_doc_id=sample_document, ty="graphrag", priority=0, fake_doc_id=GRAPH_RAPTOR_FAKE_DOC_ID, doc_ids=list(document_ids), run_mode=run_mode)
    _clear_graph_summary_cache(kb_id)

    if resume_from_task_id:
        redis_raw = getattr(REDIS_CONN, "REDIS", REDIS_CONN) or REDIS_CONN
        redis_raw.setex(f"{RESUME_PREFIX}{task_id}", DOC_TTL, resume_from_task_id)

    if not KnowledgebaseService.update_by_id(kb.id, {"graphrag_task_id": task_id}):
        logging.warning(f"Cannot save graphrag_task_id for kb {kb_id}")

    return get_json_result(data={"graphrag_task_id": task_id, "mode": run_mode, "resumed": bool(resume_from_task_id)})


@manager.route("/cancel_graphrag", methods=["POST"])  # noqa: F821
@login_required
async def cancel_graphrag():
    req = await get_request_json()
    kb_id = req.get("kb_id", "")
    if not kb_id:
        return get_error_data_result(message='Lack of "KB ID"')
    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_error_data_result(message="Invalid Knowledgebase ID")
    task_id = kb.graphrag_task_id
    if not task_id:
        return get_json_result(data=True)
    # Set cancel flag in Redis (background process will detect this)
    REDIS_CONN.set(f"{task_id}-cancel", "x")
    # Immediately mark task as cancelled in DB so UI reflects it instantly
    TaskService.update_progress(task_id, {
        "progress_msg": "Task cancelled by user.",
        "progress": -1,
    })
    return get_json_result(data=True)


@manager.route("/trace_graphrag", methods=["GET"])  # noqa: F821
@login_required
def trace_graphrag():
    kb_id = request.args.get("kb_id", "")
    if not kb_id:
        return get_error_data_result(message='Lack of "KB ID"')

    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_error_data_result(message="Invalid Knowledgebase ID")

    task_id = kb.graphrag_task_id
    if not task_id:
        return get_json_result(
            data={
                "graph_summary": _build_graphrag_graph_summary(kb),
            }
        )

    ok, task = TaskService.get_by_id(task_id)
    if not ok:
        return get_json_result(
            data={
                "graph_summary": _build_graphrag_graph_summary(kb),
            }
        )

    task_data = task.to_dict()
    try:
        task_data["doc_summary"] = GraphRAGTaskMonitor().get_resumable_summary(task_id)
    except Exception as e:
        logging.warning(f"Failed to load GraphRAG doc summary for task {task_id}: {e}")
    try:
        progress = task_data.get("progress")
        try:
            progress_value = float(progress)
        except (TypeError, ValueError):
            progress_value = None
        task_running = progress_value is not None and 0 <= progress_value < 1
        task_data["graph_summary"] = _build_graphrag_graph_summary(kb, cache_only=task_running)
    except Exception as e:
        logging.warning(f"Failed to load GraphRAG graph summary for kb {kb_id}: {e}")
    return get_json_result(data=task_data)


@manager.route("/run_raptor", methods=["POST"])  # noqa: F821
@login_required
async def run_raptor():
    req = await get_request_json()

    kb_id = req.get("kb_id", "")
    if not kb_id:
        return get_error_data_result(message='Lack of "KB ID"')

    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_error_data_result(message="Invalid Knowledgebase ID")

    task_id = kb.raptor_task_id
    if task_id:
        ok, task = TaskService.get_by_id(task_id)
        if not ok:
            logging.warning(f"A valid RAPTOR task id is expected for kb {kb_id}")

        if task and task.progress not in [-1, 1]:
            return get_error_data_result(message=f"Task {task_id} in progress with status {task.progress}. A RAPTOR Task is already running.")

    documents, _ = DocumentService.get_by_kb_id(
        kb_id=kb_id,
        page_number=0,
        items_per_page=0,
        orderby="create_time",
        desc=False,
        keywords="",
        run_status=[],
        types=[],
        suffix=[],
    )
    if not documents:
        return get_error_data_result(message=f"No documents in Knowledgebase {kb_id}")

    sample_document = documents[0]
    document_ids = [document["id"] for document in documents]

    task_id = queue_raptor_o_graphrag_tasks(sample_doc_id=sample_document, ty="raptor", priority=0, fake_doc_id=GRAPH_RAPTOR_FAKE_DOC_ID, doc_ids=list(document_ids))

    if not KnowledgebaseService.update_by_id(kb.id, {"raptor_task_id": task_id}):
        logging.warning(f"Cannot save raptor_task_id for kb {kb_id}")

    return get_json_result(data={"raptor_task_id": task_id})


@manager.route("/trace_raptor", methods=["GET"])  # noqa: F821
@login_required
def trace_raptor():
    kb_id = request.args.get("kb_id", "")
    if not kb_id:
        return get_error_data_result(message='Lack of "KB ID"')

    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_error_data_result(message="Invalid Knowledgebase ID")

    task_id = kb.raptor_task_id
    if not task_id:
        return get_json_result(data={})

    ok, task = TaskService.get_by_id(task_id)
    if not ok:
        return get_error_data_result(message="RAPTOR Task Not Found or Error Occurred")

    return get_json_result(data=task.to_dict())


@manager.route("/run_mindmap", methods=["POST"])  # noqa: F821
@login_required
async def run_mindmap():
    req = await get_request_json()

    kb_id = req.get("kb_id", "")
    if not kb_id:
        return get_error_data_result(message='Lack of "KB ID"')

    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_error_data_result(message="Invalid Knowledgebase ID")

    task_id = kb.mindmap_task_id
    if task_id:
        ok, task = TaskService.get_by_id(task_id)
        if not ok:
            logging.warning(f"A valid Mindmap task id is expected for kb {kb_id}")

        if task and task.progress not in [-1, 1]:
            return get_error_data_result(message=f"Task {task_id} in progress with status {task.progress}. A Mindmap Task is already running.")

    documents, _ = DocumentService.get_by_kb_id(
        kb_id=kb_id,
        page_number=0,
        items_per_page=0,
        orderby="create_time",
        desc=False,
        keywords="",
        run_status=[],
        types=[],
        suffix=[],
    )
    if not documents:
        return get_error_data_result(message=f"No documents in Knowledgebase {kb_id}")

    sample_document = documents[0]
    document_ids = [document["id"] for document in documents]

    task_id = queue_raptor_o_graphrag_tasks(sample_doc_id=sample_document, ty="mindmap", priority=0, fake_doc_id=GRAPH_RAPTOR_FAKE_DOC_ID, doc_ids=list(document_ids))

    if not KnowledgebaseService.update_by_id(kb.id, {"mindmap_task_id": task_id}):
        logging.warning(f"Cannot save mindmap_task_id for kb {kb_id}")

    return get_json_result(data={"mindmap_task_id": task_id})


@manager.route("/trace_mindmap", methods=["GET"])  # noqa: F821
@login_required
def trace_mindmap():
    kb_id = request.args.get("kb_id", "")
    if not kb_id:
        return get_error_data_result(message='Lack of "KB ID"')

    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_error_data_result(message="Invalid Knowledgebase ID")

    task_id = kb.mindmap_task_id
    if not task_id:
        return get_json_result(data={})

    ok, task = TaskService.get_by_id(task_id)
    if not ok:
        return get_error_data_result(message="Mindmap Task Not Found or Error Occurred")

    return get_json_result(data=task.to_dict())


@manager.route("/unbind_task", methods=["DELETE"])  # noqa: F821
@login_required
def delete_kb_task():
    kb_id = request.args.get("kb_id", "")
    if not kb_id:
        return get_error_data_result(message='Lack of "KB ID"')
    ok, kb = KnowledgebaseService.get_by_id(kb_id)
    if not ok:
        return get_json_result(data=True)

    pipeline_task_type = request.args.get("pipeline_task_type", "")
    if not pipeline_task_type or pipeline_task_type not in [PipelineTaskType.GRAPH_RAG, PipelineTaskType.RAPTOR, PipelineTaskType.MINDMAP]:
        return get_error_data_result(message="Invalid task type")

    def cancel_task(task_id):
        REDIS_CONN.set(f"{task_id}-cancel", "x")

    kb_task_id_field: str = ""
    kb_task_finish_at: str = ""
    match pipeline_task_type:
        case PipelineTaskType.GRAPH_RAG:
            kb_task_id_field = "graphrag_task_id"
            task_id = kb.graphrag_task_id
            kb_task_finish_at = "graphrag_task_finish_at"
            cancel_task(task_id)
            settings.docStoreConn.delete({"knowledge_graph_kwd": ["graph", "subgraph", "entity", "relation", "community_report", "ty2ents"]}, search.index_name(kb.tenant_id), kb_id)
            _clear_graph_summary_cache(kb_id)
        case PipelineTaskType.RAPTOR:
            kb_task_id_field = "raptor_task_id"
            task_id = kb.raptor_task_id
            kb_task_finish_at = "raptor_task_finish_at"
            cancel_task(task_id)
            settings.docStoreConn.delete({"raptor_kwd": ["raptor"]}, search.index_name(kb.tenant_id), kb_id)
        case PipelineTaskType.MINDMAP:
            kb_task_id_field = "mindmap_task_id"
            task_id = kb.mindmap_task_id
            kb_task_finish_at = "mindmap_task_finish_at"
            cancel_task(task_id)
        case _:
            return get_error_data_result(message="Internal Error: Invalid task type")


    ok = KnowledgebaseService.update_by_id(kb_id, {kb_task_id_field: "", kb_task_finish_at: None})
    if not ok:
        return server_error_response(f"Internal error: cannot delete task {pipeline_task_type}")

    return get_json_result(data=True)

@manager.route("/check_embedding", methods=["post"])  # noqa: F821
@login_required
async def check_embedding():

    def _guess_vec_field(src: dict) -> str | None:
        for k in src or {}:
            if k.endswith("_vec"):
                return k
        return None

    def _as_float_vec(v):
        if v is None:
            return []
        if isinstance(v, str):
            return [float(x) for x in v.split("\t") if x != ""]
        if isinstance(v, (list, tuple, np.ndarray)):
            return [float(x) for x in v]
        return []

    def _to_1d(x):
        a = np.asarray(x, dtype=np.float32)
        return a.reshape(-1)

    def _cos_sim(a, b, eps=1e-12):
        a = _to_1d(a)
        b = _to_1d(b)
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na < eps or nb < eps:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def sample_random_chunks_with_vectors(
        docStoreConn,
        tenant_id: str,
        kb_id: str,
        n: int = 5,
        base_fields=("docnm_kwd","doc_id","content_with_weight","page_num_int","position_int","top_int"),
    ):
        index_nm = search.index_name(tenant_id)

        res0 = docStoreConn.search(
            select_fields=[], highlight_fields=[],
            condition={"kb_id": kb_id, "available_int": 1},
            match_expressions=[], order_by=OrderByExpr(),
            offset=0, limit=1,
            index_names=index_nm, knowledgebase_ids=[kb_id]
        )
        total = docStoreConn.get_total(res0)
        if total <= 0:
            return []

        n = min(n, total)
        offsets = sorted(random.sample(range(min(total,1000)), n))
        out = []

        for off in offsets:
            res1 = docStoreConn.search(
                select_fields=list(base_fields),
                highlight_fields=[],
                condition={"kb_id": kb_id, "available_int": 1},
                match_expressions=[], order_by=OrderByExpr(),
                offset=off, limit=1,
                index_names=index_nm, knowledgebase_ids=[kb_id]
            )
            ids = docStoreConn.get_doc_ids(res1)
            if not ids:
                continue

            cid = ids[0]
            full_doc = docStoreConn.get(cid, index_nm, [kb_id]) or {}
            vec_field = _guess_vec_field(full_doc)
            vec = _as_float_vec(full_doc.get(vec_field))

            out.append({
                "chunk_id": cid,
                "kb_id": kb_id,
                "doc_id": full_doc.get("doc_id"),
                "doc_name": full_doc.get("docnm_kwd"),
                "vector_field": vec_field,
                "vector_dim": len(vec),
                "vector": vec,
                "page_num_int": full_doc.get("page_num_int"),
                "position_int": full_doc.get("position_int"),
                "top_int": full_doc.get("top_int"),
                "content_with_weight": full_doc.get("content_with_weight") or "",
                "question_kwd": full_doc.get("question_kwd") or []
            })
        return out

    def _clean(s: str) -> str:
        s = re.sub(r"</?(table|td|caption|tr|th)( [^<>]{0,12})?>", " ", s or "")
        return s if s else "None"
    req = await get_request_json()
    kb_id = req.get("kb_id", "")
    embd_id = req.get("embd_id", "")
    n = int(req.get("check_num", 5))
    _, kb = KnowledgebaseService.get_by_id(kb_id)
    tenant_id = kb.tenant_id

    emb_mdl = LLMBundle(tenant_id, LLMType.EMBEDDING, embd_id)
    samples = sample_random_chunks_with_vectors(settings.docStoreConn, tenant_id=tenant_id, kb_id=kb_id, n=n)

    results, eff_sims = [], []
    for ck in samples:
        title = ck.get("doc_name") or "Title"
        txt_in = "\n".join(ck.get("question_kwd") or []) or ck.get("content_with_weight") or ""
        txt_in = _clean(txt_in)
        if not txt_in:
            results.append({"chunk_id": ck["chunk_id"], "reason": "no_text"})
            continue

        if not ck.get("vector"):
            results.append({"chunk_id": ck["chunk_id"], "reason": "no_stored_vector"})
            continue

        try:
            v, _ = emb_mdl.encode([title, txt_in])
            assert len(v[1]) == len(ck["vector"]), f"The dimension ({len(v[1])}) of given embedding model is different from the original ({len(ck['vector'])})"
            sim_content = _cos_sim(v[1], ck["vector"])
            title_w = 0.1
            qv_mix = title_w * v[0] + (1 - title_w) * v[1]
            sim_mix = _cos_sim(qv_mix, ck["vector"])
            sim = sim_content
            mode = "content_only"
            if sim_mix > sim:
                sim = sim_mix
                mode = "title+content"
        except Exception as e:
            return get_error_data_result(message=f"Embedding failure. {e}")

        eff_sims.append(sim)
        results.append({
            "chunk_id": ck["chunk_id"],
            "doc_id": ck["doc_id"],
            "doc_name": ck["doc_name"],
            "vector_field": ck["vector_field"],
            "vector_dim": ck["vector_dim"],
            "cos_sim": round(sim, 6),
        })

    summary = {
        "kb_id": kb_id,
        "model": embd_id,
        "sampled": len(samples),
        "valid": len(eff_sims),
        "avg_cos_sim": round(float(np.mean(eff_sims)) if eff_sims else 0.0, 6),
        "min_cos_sim": round(float(np.min(eff_sims)) if eff_sims else 0.0, 6),
        "max_cos_sim": round(float(np.max(eff_sims)) if eff_sims else 0.0, 6),
        "match_mode": mode,
    }
    if summary["avg_cos_sim"] > 0.9:
        return get_json_result(data={"summary": summary, "results": results})
    return get_json_result(code=RetCode.NOT_EFFECTIVE, message="Embedding model switch failed: the average similarity between old and new vectors is below 0.9, indicating incompatible vector spaces.", data={"summary": summary, "results": results})

