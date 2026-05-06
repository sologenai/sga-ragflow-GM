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
import asyncio
import json
import logging
import os
import random
import time

import networkx as nx

from api.db.services.document_service import DocumentService
from api.db.services.task_service import has_canceled
from common.exceptions import TaskCanceledException
from common.misc_utils import get_uuid
from rag.graphrag.entity_resolution import EntityResolution
from rag.graphrag.general.community_reports_extractor import CommunityReportsExtractor
from rag.graphrag.general.extractor import Extractor
from rag.graphrag.general.graph_extractor import GraphExtractor as GeneralKGExt
from rag.graphrag.light.graph_extractor import GraphExtractor as LightKGExt
from rag.graphrag.utils import (
    GraphChange,
    chunk_id,
    does_graph_contains,
    get_graph,
    get_graph_doc_ids,
    graph_merge,
    set_graph,
    tidy_graph,
)
from common.misc_utils import thread_pool_exec
from rag.nlp import rag_tokenizer, search
from rag.graphrag.task_monitor import GraphRAGTaskMonitor
from rag.utils.redis_conn import RedisDistributedLock
from common import settings


def _read_env_int(name: str, default: int, min_value: int = 0) -> int:
    raw = os.environ.get(name, str(default))
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        parsed = default
    return max(parsed, min_value)


def _read_env_float(name: str, default: float, min_value: float = 0.0) -> float:
    raw = os.environ.get(name, str(default))
    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        parsed = default
    return max(parsed, min_value)


GRAPHRAG_DOC_MAX_RETRIES = _read_env_int("GRAPHRAG_DOC_MAX_RETRIES", 0, min_value=0)
GRAPHRAG_STAGE_MAX_RETRIES = _read_env_int("GRAPHRAG_STAGE_MAX_RETRIES", 0, min_value=0)
GRAPHRAG_STAGE_RETRY_BASE_SECONDS = _read_env_float("GRAPHRAG_STAGE_RETRY_BASE_SECONDS", 5.0, min_value=0.0)
GRAPHRAG_STAGE_RETRY_MAX_SECONDS = _read_env_float("GRAPHRAG_STAGE_RETRY_MAX_SECONDS", 300.0, min_value=0.0)


def _retry_limit_label(max_retries: int) -> str:
    return "unlimited" if max_retries <= 0 else str(max_retries)


def _is_non_retryable_graphrag_error(exc: Exception) -> bool:
    message = str(exc).lower()
    hard_error_keywords = (
        "not authorized",
        "unauthorized",
        "forbidden",
        "permission denied",
        "invalid api key",
        "invalid token",
        "authentication",
        "model not found",
        "not found",
        "not support",
        "unsupported",
        "dimension",
        "mapping",
        "schema",
    )
    return any(keyword in message for keyword in hard_error_keywords)


def _is_transient_graphrag_error(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError, ConnectionError, OSError)):
        return True
    if _is_non_retryable_graphrag_error(exc):
        return False
    message = str(exc).lower()
    transient_keywords = (
        "timeout",
        "timed out",
        "rate limit",
        "too many request",
        "quota",
        "temporarily",
        "temporary",
        "try again",
        "retry",
        "connection",
        "reset",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "503",
        "502",
        "504",
        "429",
    )
    return any(keyword in message for keyword in transient_keywords)


async def _sleep_before_retry(stage: str, attempt: int, max_retries: int, callback, reason: Exception):
    delay = min(
        GRAPHRAG_STAGE_RETRY_MAX_SECONDS,
        GRAPHRAG_STAGE_RETRY_BASE_SECONDS * (2 ** max(0, attempt - 1)),
    ) if GRAPHRAG_STAGE_RETRY_BASE_SECONDS > 0 else 0.0
    jitter = random.uniform(0, max(0.5, delay * 0.2)) if delay > 0 else random.uniform(0.0, 0.3)
    wait_seconds = delay + jitter
    callback(
        msg=(
            f"[GraphRAG] retry {stage} attempt {attempt + 1}/{_retry_limit_label(max_retries)} "
            f"in {wait_seconds:.2f}s (reason={reason!r})"
        )
    )
    await asyncio.sleep(wait_seconds)


async def _run_resilient_stage(stage: str, operation, callback, *, max_retries: int = GRAPHRAG_STAGE_MAX_RETRIES):
    attempt = 0
    while True:
        attempt += 1
        try:
            return await operation()
        except TaskCanceledException:
            raise
        except Exception as exc:
            retryable = _is_transient_graphrag_error(exc)
            attempts_exhausted = max_retries > 0 and attempt >= max_retries
            if (not retryable) or attempts_exhausted:
                raise
            await _sleep_before_retry(stage, attempt, max_retries, callback, exc)


async def run_graphrag(
    row: dict,
    language,
    with_resolution: bool,
    with_community: bool,
    chat_model,
    embedding_model,
    callback,
):
    enable_timeout_assertion = os.environ.get("ENABLE_TIMEOUT_ASSERTION")
    start = asyncio.get_running_loop().time()
    tenant_id, kb_id, doc_id = row["tenant_id"], str(row["kb_id"]), row["doc_id"]
    chunks = []
    for d in settings.retriever.chunk_list(doc_id, tenant_id, [kb_id], max_count=10000, fields=["content_with_weight", "doc_id"], sort_by_position=True):
        chunks.append(d["content_with_weight"])

    timeout_sec = max(120, len(chunks) * 60 * 10) if enable_timeout_assertion else 10000000000

    try:
        subgraph = await asyncio.wait_for(
            generate_subgraph(
                LightKGExt if "method" not in row["kb_parser_config"].get("graphrag", {})
                    or row["kb_parser_config"]["graphrag"]["method"] != "general"
                else GeneralKGExt,
                tenant_id,
                kb_id,
                doc_id,
                chunks,
                language,
                row["kb_parser_config"]["graphrag"].get("entity_types", []),
                chat_model,
                embedding_model,
                callback,
            ),
            timeout=timeout_sec,
        )
    except asyncio.TimeoutError:
        logging.error("generate_subgraph timeout")
        raise

    if not subgraph:
        return

    graphrag_task_lock = RedisDistributedLock(f"graphrag_task_{kb_id}", lock_value=doc_id, timeout=1200)
    await graphrag_task_lock.spin_acquire()
    callback(msg=f"run_graphrag {doc_id} graphrag_task_lock acquired")

    try:
        subgraph_nodes = set(subgraph.nodes())
        new_graph = await merge_subgraph(
            tenant_id,
            kb_id,
            doc_id,
            subgraph,
            embedding_model,
            callback,
        )
        assert new_graph is not None

        if not with_resolution and not with_community:
            return

        if with_resolution:
            await graphrag_task_lock.spin_acquire()
            callback(msg=f"run_graphrag {doc_id} graphrag_task_lock acquired")
            await resolve_entities(
                new_graph,
                subgraph_nodes,
                tenant_id,
                kb_id,
                doc_id,
                chat_model,
                embedding_model,
                callback,
                task_id=row["id"],
            )
        if with_community:
            await graphrag_task_lock.spin_acquire()
            callback(msg=f"run_graphrag {doc_id} graphrag_task_lock acquired")
            await extract_community(
                new_graph,
                tenant_id,
                kb_id,
                doc_id,
                chat_model,
                embedding_model,
                callback,
                task_id=row["id"],
            )
    finally:
        graphrag_task_lock.release()
    now = asyncio.get_running_loop().time()
    callback(msg=f"GraphRAG for doc {doc_id} done in {now - start:.2f} seconds.")
    return


async def run_graphrag_for_kb(
    row: dict,
    doc_ids: list[str],
    language: str,
    kb_parser_config: dict,
    chat_model,
    embedding_model,
    callback,
    *,
    with_resolution: bool = True,
    with_community: bool = True,
    max_parallel_docs: int = 4,
) -> dict:
    tenant_id, kb_id = row["tenant_id"], row["kb_id"]
    task_id = row["id"]
    monitor = GraphRAGTaskMonitor()
    run_mode = row.get("graphrag_run_mode") or "incremental"
    enable_timeout_assertion = os.environ.get("ENABLE_TIMEOUT_ASSERTION")
    start = asyncio.get_running_loop().time()
    fields_for_chunks = ["content_with_weight", "doc_id"]

    if not doc_ids:
        logging.info(f"Fetching all docs for {kb_id}")
        docs, _ = DocumentService.get_by_kb_id(
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
        doc_ids = [doc["id"] for doc in docs]

    doc_ids = list(dict.fromkeys(doc_ids))
    if not doc_ids:
        callback(msg=f"[GraphRAG] kb:{kb_id} has no processable doc_id.")
        return {"ok_docs": [], "failed_docs": [], "total_docs": 0, "total_chunks": 0, "seconds": 0.0}

    def get_doc_name(doc_id: str) -> str:
        try:
            _, doc_obj = DocumentService.get_by_id(doc_id)
            return doc_obj.name if doc_obj else doc_id[:8]
        except Exception:
            return doc_id[:8]

    resume_from = monitor.get_resume_from_task_id(task_id)
    prev_merged_doc_ids = set(monitor.get_merged_doc_ids(resume_from)) if resume_from else set()
    graph_doc_ids = set()
    try:
        graph_doc_ids = set(await get_graph_doc_ids(tenant_id, kb_id))
    except Exception as e:
        logging.warning("Failed to load existing GraphRAG doc ids for kb %s: %s", kb_id, e)

    can_skip_existing_docs = run_mode in {"incremental", "resume_failed"}
    skip_doc_ids = (prev_merged_doc_ids | graph_doc_ids).intersection(doc_ids) if can_skip_existing_docs else set()
    process_doc_ids = [doc_id for doc_id in doc_ids if doc_id not in skip_doc_ids]
    if resume_from:
        callback(
            msg=(
                f"[GraphRAG] resume from task {resume_from}: skip {len(skip_doc_ids)} "
                f"merged docs, process {len(process_doc_ids)} docs."
            )
        )
    elif run_mode == "incremental":
        callback(
            msg=(
                f"[GraphRAG] incremental update: skip {len(skip_doc_ids)} existing docs, "
                f"process {len(process_doc_ids)} docs."
            )
        )
    elif run_mode == "regenerate":
        callback(msg=f"[GraphRAG] regenerate mode: rebuild graph from {len(process_doc_ids)} docs.")

    def load_doc_chunks(doc_id: str) -> list[str]:
        from common.token_utils import num_tokens_from_string

        chunks = []
        current_chunk = ""

        raw_chunks = list(settings.retriever.chunk_list(
            doc_id,
            tenant_id,
            [kb_id],
            max_count=10000,
            fields=fields_for_chunks,
            sort_by_position=True,
        ))

        callback(msg=f"[DEBUG] chunk_list() returned {len(raw_chunks)} raw chunks for doc {doc_id}")

        for d in raw_chunks:
            content = d["content_with_weight"]
            if num_tokens_from_string(current_chunk + content) < 4096:
                current_chunk += content
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = content

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    all_doc_chunks: dict[str, list[str]] = {}
    total_chunks = 0
    for doc_id in process_doc_ids:
        chunks = load_doc_chunks(doc_id)
        all_doc_chunks[doc_id] = chunks
        total_chunks += len(chunks)

    doc_info_list = [
        {
            "doc_id": doc_id,
            "doc_name": get_doc_name(doc_id),
            "chunk_count": len(all_doc_chunks.get(doc_id, [])),
        }
        for doc_id in doc_ids
    ]
    monitor.init_doc_progress(task_id, doc_info_list, resume_from_task_id=resume_from)

    skipped_docs: list[str] = []
    for doc_id in doc_ids:
        if doc_id in skip_doc_ids:
            skipped_docs.append(doc_id)
            monitor.update_doc_status(task_id, doc_id, "skipped", end_time=time.time())
    if skipped_docs:
        callback(msg=f"[GraphRAG] skipped {len(skipped_docs)} docs already present in graph.")

    semaphore = asyncio.Semaphore(max_parallel_docs)

    subgraphs: dict[str, object] = {}
    failed_docs: list[tuple[str, str]] = []  # (doc_id, error)

    async def run_post_processing(final_graph, subgraph_nodes: set):
        if not with_resolution and not with_community:
            return
        if final_graph is None:
            raise RuntimeError("global graph is unavailable before GraphRAG post-processing")
        if has_canceled(task_id):
            callback(msg=f"Task {task_id} cancelled before resolution/community extraction.")
            raise TaskCanceledException(f"Task {task_id} was cancelled")

        kb_lock = RedisDistributedLock(f"graphrag_task_{kb_id}", lock_value="post_process", timeout=1200)
        await kb_lock.spin_acquire()
        callback(msg=f"[GraphRAG] kb:{kb_id} post-merge lock acquired for resolution/community")

        try:
            if with_resolution:
                await _run_resilient_stage(
                    "entity_resolution",
                    lambda: resolve_entities(
                        final_graph,
                        subgraph_nodes,
                        tenant_id,
                        kb_id,
                        None,
                        chat_model,
                        embedding_model,
                        callback,
                        task_id=task_id,
                    ),
                    callback,
                )

            if with_community:
                await _run_resilient_stage(
                    "community_extraction",
                    lambda: extract_community(
                        final_graph,
                        tenant_id,
                        kb_id,
                        None,
                        chat_model,
                        embedding_model,
                        callback,
                        task_id=task_id,
                    ),
                    callback,
                )
        finally:
            kb_lock.release()

    async def build_one(doc_id: str):
        if has_canceled(task_id):
            callback(msg=f"Task {task_id} cancelled, stopping execution.")
            raise TaskCanceledException(f"Task {task_id} was cancelled")

        chunks = all_doc_chunks.get(doc_id, [])
        if not chunks:
            skipped_docs.append(doc_id)
            monitor.update_doc_status(task_id, doc_id, "skipped", end_time=time.time())
            callback(msg=f"[GraphRAG] doc:{doc_id} has no available chunks, skip generation.")
            return

        if await does_graph_contains(tenant_id, kb_id, doc_id):
            skipped_docs.append(doc_id)
            monitor.update_doc_status(task_id, doc_id, "skipped", end_time=time.time())
            callback(msg=f"[GraphRAG] doc:{doc_id} already exists in graph, skip generation.")
            return

        kg_extractor = LightKGExt if ("method" not in kb_parser_config.get("graphrag", {}) or kb_parser_config["graphrag"]["method"] != "general") else GeneralKGExt

        deadline = max(120, len(chunks) * 60 * 10) if enable_timeout_assertion else 10000000000

        async with semaphore:
            try:
                msg = f"[GraphRAG] build_subgraph doc:{doc_id}"
                monitor.update_doc_status(task_id, doc_id, "extracting", start_time=time.time())
                callback(msg=f"{msg} start (chunks={len(chunks)}, timeout={deadline}s)")

                try:
                    sg = await _run_resilient_stage(
                        f"build_subgraph doc:{doc_id}",
                        lambda: asyncio.wait_for(
                            generate_subgraph(
                                kg_extractor,
                                tenant_id,
                                kb_id,
                                doc_id,
                                chunks,
                                language,
                                kb_parser_config.get("graphrag", {}).get("entity_types", []),
                                chat_model,
                                embedding_model,
                                callback,
                                task_id=task_id
                            ),
                            timeout=deadline,
                        ),
                        callback,
                        max_retries=GRAPHRAG_DOC_MAX_RETRIES,
                    )
                except asyncio.TimeoutError:
                    failed_docs.append((doc_id, "timeout"))
                    monitor.update_doc_status(task_id, doc_id, "failed", error="timeout", end_time=time.time())
                    callback(msg=f"{msg} FAILED: timeout")
                    return
                except Exception as e:
                    if _is_non_retryable_graphrag_error(e):
                        callback(msg=f"{msg} FAILED: non-retryable configuration/model error: {e!r}")
                    raise
                if sg:
                    subgraphs[doc_id] = sg
                    monitor.update_doc_status(
                        task_id,
                        doc_id,
                        "extracted",
                        entity_count=len(sg.nodes()),
                        relation_count=len(sg.edges()),
                        end_time=time.time(),
                    )
                    callback(msg=f"{msg} done")
                else:
                    failed_docs.append((doc_id, "subgraph is empty"))
                    monitor.update_doc_status(task_id, doc_id, "failed", error="subgraph is empty", end_time=time.time())
                    callback(msg=f"{msg} empty")
            except TaskCanceledException as canceled:
                monitor.update_doc_status(task_id, doc_id, "failed", error=str(canceled), end_time=time.time())
                callback(msg=f"[GraphRAG] build_subgraph doc:{doc_id} FAILED: {canceled}")
                raise
            except Exception as e:
                failed_docs.append((doc_id, repr(e)))
                monitor.update_doc_status(task_id, doc_id, "failed", error=repr(e), end_time=time.time())
                callback(msg=f"[GraphRAG] build_subgraph doc:{doc_id} FAILED: {e!r}")

    if has_canceled(task_id):
        callback(msg=f"Task {task_id} cancelled before processing documents.")
        raise TaskCanceledException(f"Task {task_id} was cancelled")

    tasks = [asyncio.create_task(build_one(doc_id)) for doc_id in process_doc_ids]
    try:
        await asyncio.gather(*tasks, return_exceptions=False)
    except Exception as e:
        logging.error(f"Error in asyncio.gather: {e}")
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise

    if has_canceled(task_id):
        callback(msg=f"Task {task_id} cancelled after document processing.")
        raise TaskCanceledException(f"Task {task_id} was cancelled")

    ok_docs = [d for d in process_doc_ids if d in subgraphs]
    if not ok_docs:
        if resume_from and not failed_docs and (with_resolution or with_community):
            final_graph = await get_graph(tenant_id, kb_id)
            if final_graph is not None:
                callback(msg=f"[GraphRAG] no new documents; resume post-processing on existing graph.")
                await run_post_processing(final_graph, set(final_graph.nodes()))
        callback(msg=f"[GraphRAG] kb:{kb_id} no new subgraphs generated, end.")
        now = asyncio.get_running_loop().time()
        return {
            "ok_docs": [],
            "skipped_docs": skipped_docs,
            "failed_docs": failed_docs,
            "total_docs": len(doc_ids),
            "total_chunks": total_chunks,
            "seconds": now - start,
        }

    kb_lock = RedisDistributedLock(f"graphrag_task_{kb_id}", lock_value="batch_merge", timeout=1200)
    await kb_lock.spin_acquire()
    callback(msg=f"[GraphRAG] kb:{kb_id} merge lock acquired")

    if has_canceled(task_id):
        callback(msg=f"Task {task_id} cancelled before merging subgraphs.")
        raise TaskCanceledException(f"Task {task_id} was cancelled")

    union_nodes: set = set()
    final_graph = None
    try:
        for idx, doc_id in enumerate(ok_docs):
            sg = subgraphs[doc_id]
            union_nodes.update(set(sg.nodes()))

            try:
                new_graph = await _run_resilient_stage(
                    f"merge_subgraph doc:{doc_id}",
                    lambda: merge_subgraph(
                        tenant_id,
                        kb_id,
                        doc_id,
                        sg,
                        embedding_model,
                        callback,
                    ),
                    callback,
                )
            except Exception as e:
                failed_docs.append((doc_id, repr(e)))
                monitor.update_doc_status(task_id, doc_id, "failed", error=repr(e), end_time=time.time())
                raise
            if new_graph is not None:
                final_graph = new_graph
                monitor.update_doc_status(task_id, doc_id, "merged", end_time=time.time())
            callback(
                prog=0.6 + 0.2 * ((idx + 1) / max(len(ok_docs), 1)),
                msg=f"[GraphRAG] merge progress: {idx + 1}/{len(ok_docs)}",
            )

        if final_graph is None:
            callback(msg=f"[GraphRAG] kb:{kb_id} merge finished (no in-memory graph returned).")
        else:
            callback(msg=f"[GraphRAG] kb:{kb_id} merge finished, graph ready.")
    finally:
        kb_lock.release()

    if failed_docs:
        now = asyncio.get_running_loop().time()
        callback(
            msg=(
                f"[GraphRAG] pause before post-processing because {len(failed_docs)} docs failed. "
                "Resume after fixing model quota/timeout to process remaining docs."
            )
        )
        return {
            "ok_docs": ok_docs,
            "skipped_docs": skipped_docs,
            "failed_docs": failed_docs,
            "total_docs": len(doc_ids),
            "total_chunks": total_chunks,
            "seconds": now - start,
        }

    if not with_resolution and not with_community:
        now = asyncio.get_running_loop().time()
        counts = monitor.get_counts(task_id)
        callback(msg=f"[GraphRAG] KB merge done in {now - start:.2f}s. ok={len(ok_docs)} skipped={len(skipped_docs)} failed={len(failed_docs)} total={len(doc_ids)} counts={counts}")
        return {
            "ok_docs": ok_docs,
            "skipped_docs": skipped_docs,
            "failed_docs": failed_docs,
            "total_docs": len(doc_ids),
            "total_chunks": total_chunks,
            "seconds": now - start,
        }

    if final_graph is None:
        final_graph = await get_graph(tenant_id, kb_id)
    if final_graph is None:
        failed_docs.append(("__graph__", "global graph is unavailable before post-processing"))
        now = asyncio.get_running_loop().time()
        return {
            "ok_docs": ok_docs,
            "skipped_docs": skipped_docs,
            "failed_docs": failed_docs,
            "total_docs": len(doc_ids),
            "total_chunks": total_chunks,
            "seconds": now - start,
        }
    await run_post_processing(final_graph, union_nodes or set(final_graph.nodes()))

    now = asyncio.get_running_loop().time()
    counts = monitor.get_counts(task_id)
    callback(msg=f"[GraphRAG] GraphRAG for KB {kb_id} done in {now - start:.2f} seconds. ok={len(ok_docs)} skipped={len(skipped_docs)} failed={len(failed_docs)} total_docs={len(doc_ids)} total_chunks={total_chunks} counts={counts}")
    return {
        "ok_docs": ok_docs,
        "skipped_docs": skipped_docs,
        "failed_docs": failed_docs,  # [(doc_id, error), ...]
        "total_docs": len(doc_ids),
        "total_chunks": total_chunks,
        "seconds": now - start,
    }


async def generate_subgraph(
    extractor: Extractor,
    tenant_id: str,
    kb_id: str,
    doc_id: str,
    chunks: list[str],
    language,
    entity_types,
    llm_bdl,
    embed_bdl,
    callback,
    task_id: str = "",
):
    if task_id and has_canceled(task_id):
        callback(msg=f"Task {task_id} cancelled during subgraph generation for doc {doc_id}.")
        raise TaskCanceledException(f"Task {task_id} was cancelled")

    contains = await does_graph_contains(tenant_id, kb_id, doc_id)
    if contains:
        callback(msg=f"Graph already contains {doc_id}")
        return None
    start = asyncio.get_running_loop().time()
    ext = extractor(
        llm_bdl,
        language=language,
        entity_types=entity_types,
    )

    # Our customization: get doc name for Chinese-style logging
    try:
        _, doc_info = DocumentService.get_by_id(doc_id)
        doc_name = doc_info.name if doc_info else doc_id[:8]
    except Exception:
        doc_name = doc_id[:8]

    callback(msg=f"[>] {doc_name} 开始处理 (共 {len(chunks)} 个分块)")
    ents, rels = await ext(doc_id, chunks, callback, task_id=task_id, doc_name=doc_name)
    subgraph = nx.Graph()

    for ent in ents:
        if task_id and has_canceled(task_id):
            callback(msg=f"Task {task_id} cancelled during entity processing for doc {doc_id}.")
            raise TaskCanceledException(f"Task {task_id} was cancelled")

        assert "description" in ent, f"entity {ent} does not have description"
        ent["source_id"] = [doc_id]
        subgraph.add_node(ent["entity_name"], **ent)

    ignored_rels = 0
    for rel in rels:
        if task_id and has_canceled(task_id):
            callback(msg=f"Task {task_id} cancelled during relationship processing for doc {doc_id}.")
            raise TaskCanceledException(f"Task {task_id} was cancelled")

        assert "description" in rel, f"relation {rel} does not have description"
        if not subgraph.has_node(rel["src_id"]) or not subgraph.has_node(rel["tgt_id"]):
            ignored_rels += 1
            continue
        rel["source_id"] = [doc_id]
        subgraph.add_edge(
            rel["src_id"],
            rel["tgt_id"],
            **rel,
        )
    if ignored_rels:
        callback(msg=f"ignored {ignored_rels} relations due to missing entities.")
    tidy_graph(subgraph, callback, check_attribute=False)

    subgraph.graph["source_id"] = [doc_id]
    chunk = {
        "content_with_weight": json.dumps(nx.node_link_data(subgraph, edges="edges"), ensure_ascii=False),
        "knowledge_graph_kwd": "subgraph",
        "kb_id": kb_id,
        "source_id": [doc_id],
        "available_int": 0,
        "removed_kwd": "N",
    }
    cid = chunk_id(chunk)
    await thread_pool_exec(settings.docStoreConn.delete,{"knowledge_graph_kwd": "subgraph", "source_id": doc_id},search.index_name(tenant_id),kb_id,)
    await thread_pool_exec(settings.docStoreConn.insert,[{"id": cid, **chunk}],search.index_name(tenant_id),kb_id,)
    now = asyncio.get_running_loop().time()
    callback(msg=f"[OK] {doc_name} 子图生成完成 ({now - start:.2f}s)")
    return subgraph


async def merge_subgraph(
    tenant_id: str,
    kb_id: str,
    doc_id: str,
    subgraph: nx.Graph,
    embedding_model,
    callback,
):
    start = asyncio.get_running_loop().time()
    change = GraphChange()
    old_graph = await get_graph(tenant_id, kb_id, subgraph.graph["source_id"])
    if old_graph is not None:
        logging.info("Merge with an exiting graph...................")
        tidy_graph(old_graph, callback)
        new_graph = graph_merge(old_graph, subgraph, change)
    else:
        new_graph = subgraph
        change.added_updated_nodes = set(new_graph.nodes())
        change.added_updated_edges = set(new_graph.edges())
    pr = nx.pagerank(new_graph)
    for node_name, pagerank in pr.items():
        new_graph.nodes[node_name]["pagerank"] = pagerank

    await set_graph(tenant_id, kb_id, embedding_model, new_graph, change, callback)
    now = asyncio.get_running_loop().time()
    callback(msg=f"merging subgraph for doc {doc_id} into the global graph done in {now - start:.2f} seconds.")
    return new_graph


async def resolve_entities(
    graph,
    subgraph_nodes: set[str],
    tenant_id: str,
    kb_id: str,
    doc_id: str,
    llm_bdl,
    embed_bdl,
    callback,
    task_id: str = "",
):
    # Check if task has been canceled before resolution
    if task_id and has_canceled(task_id):
        callback(msg=f"Task {task_id} cancelled during entity resolution.")
        raise TaskCanceledException(f"Task {task_id} was cancelled")

    start = asyncio.get_running_loop().time()
    er = EntityResolution(
        llm_bdl,
    )
    reso = await er(graph, subgraph_nodes, callback=callback, task_id=task_id)
    graph = reso.graph
    change = reso.change
    callback(msg=f"Graph resolution removed {len(change.removed_nodes)} nodes and {len(change.removed_edges)} edges.")
    callback(msg="Graph resolution updated pagerank.")

    if task_id and has_canceled(task_id):
        callback(msg=f"Task {task_id} cancelled after entity resolution.")
        raise TaskCanceledException(f"Task {task_id} was cancelled")

    await set_graph(tenant_id, kb_id, embed_bdl, graph, change, callback)
    now = asyncio.get_running_loop().time()
    callback(msg=f"Graph resolution done in {now - start:.2f}s.")


async def extract_community(
    graph,
    tenant_id: str,
    kb_id: str,
    doc_id: str,
    llm_bdl,
    embed_bdl,
    callback,
    task_id: str = "",
):
    if task_id and has_canceled(task_id):
        callback(msg=f"Task {task_id} cancelled before community extraction.")
        raise TaskCanceledException(f"Task {task_id} was cancelled")

    start = asyncio.get_running_loop().time()
    ext = CommunityReportsExtractor(
        llm_bdl,
    )
    cr = await ext(graph, callback=callback, task_id=task_id)

    if task_id and has_canceled(task_id):
        callback(msg=f"Task {task_id} cancelled during community extraction.")
        raise TaskCanceledException(f"Task {task_id} was cancelled")

    community_structure = cr.structured_output
    community_reports = cr.output
    doc_ids = graph.graph["source_id"]

    now = asyncio.get_running_loop().time()
    callback(msg=f"Graph extracted {len(cr.structured_output)} communities in {now - start:.2f}s.")
    start = now
    if task_id and has_canceled(task_id):
        callback(msg=f"Task {task_id} cancelled during community indexing.")
        raise TaskCanceledException(f"Task {task_id} was cancelled")

    chunks = []
    for stru, rep in zip(community_structure, community_reports):
        obj = {
            "report": rep,
            "evidences": "\n".join([f.get("explanation", "") for f in stru["findings"]]),
        }
        chunk = {
            "id": get_uuid(),
            "docnm_kwd": stru["title"],
            "title_tks": rag_tokenizer.tokenize(stru["title"]),
            "content_with_weight": json.dumps(obj, ensure_ascii=False),
            "content_ltks": rag_tokenizer.tokenize(obj["report"] + " " + obj["evidences"]),
            "knowledge_graph_kwd": "community_report",
            "weight_flt": stru["weight"],
            "entities_kwd": stru["entities"],
            "important_kwd": stru["entities"],
            "kb_id": kb_id,
            "source_id": list(doc_ids),
            "available_int": 0,
        }
        chunk["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(chunk["content_ltks"])
        chunks.append(chunk)

    await thread_pool_exec(settings.docStoreConn.delete,{"knowledge_graph_kwd": "community_report", "kb_id": kb_id},search.index_name(tenant_id),kb_id,)
    es_bulk_size = 4
    for b in range(0, len(chunks), es_bulk_size):
        doc_store_result = await thread_pool_exec(settings.docStoreConn.insert,chunks[b : b + es_bulk_size],search.index_name(tenant_id),kb_id,)
        if doc_store_result:
            error_message = f"Insert chunk error: {doc_store_result}, please check log file and Elasticsearch/Infinity status!"
            raise Exception(error_message)

    if task_id and has_canceled(task_id):
        callback(msg=f"Task {task_id} cancelled after community indexing.")
        raise TaskCanceledException(f"Task {task_id} was cancelled")

    now = asyncio.get_running_loop().time()
    callback(msg=f"Graph indexed {len(cr.structured_output)} communities in {now - start:.2f}s.")
    return community_structure, community_reports
