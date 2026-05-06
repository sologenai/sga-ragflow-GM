# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

from common.misc_utils import thread_pool_exec

"""
Reference:
 - [graphrag](https://github.com/microsoft/graphrag)
 - [LightRag](https://github.com/HKUDS/LightRAG)
"""

import asyncio
import dataclasses
import html
import json
import logging
import os
import random
import re
import time
from collections import defaultdict
from hashlib import md5
from typing import Any, Callable, Set, Tuple

import networkx as nx
import numpy as np
import xxhash
from networkx.readwrite import json_graph

from common.misc_utils import get_uuid
from common.connection_utils import timeout
from rag.nlp import rag_tokenizer, search
from rag.utils.redis_conn import REDIS_CONN
from common import settings
from common.doc_store.doc_store_base import OrderByExpr

GRAPH_FIELD_SEP = "<SEP>"

ErrorHandlerFn = Callable[[BaseException | None, str | None, dict | None], None]

chat_limiter = asyncio.Semaphore(int(os.environ.get("MAX_CONCURRENT_CHATS", 10)))


def _read_env_int(name: str, default: int, min_value: int = 1) -> int:
    raw = os.environ.get(name, str(default))
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        parsed = default
    if parsed < min_value:
        return min_value
    return parsed


def _read_env_float(name: str, default: float, min_value: float = 0.0) -> float:
    raw = os.environ.get(name, str(default))
    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        parsed = default
    if parsed < min_value:
        return min_value
    return parsed


GRAPHRAG_EMBED_BATCH_SIZE = _read_env_int("GRAPHRAG_EMBED_BATCH_SIZE", 16, min_value=1)
GRAPHRAG_EMBED_CONCURRENCY = _read_env_int("GRAPHRAG_EMBED_CONCURRENCY", 2, min_value=1)
GRAPHRAG_EMBED_MAX_RETRIES = _read_env_int("GRAPHRAG_EMBED_MAX_RETRIES", 0, min_value=0)
GRAPHRAG_EMBED_RETRY_BASE_SECONDS = _read_env_float("GRAPHRAG_EMBED_RETRY_BASE_SECONDS", 2.0, min_value=0.0)
GRAPHRAG_EMBED_RETRY_MAX_SECONDS = _read_env_float("GRAPHRAG_EMBED_RETRY_MAX_SECONDS", 60.0, min_value=0.0)
GRAPHRAG_EMBED_ATTEMPT_TIMEOUT_SECONDS = _read_env_float("GRAPHRAG_EMBED_ATTEMPT_TIMEOUT_SECONDS", 60 * 60, min_value=0.0)
GRAPHRAG_EMBED_MAX_ATTEMPT_TIMEOUT_SECONDS = _read_env_float(
    "GRAPHRAG_EMBED_MAX_ATTEMPT_TIMEOUT_SECONDS",
    60 * 60 * 6,
    min_value=0.0,
)
GRAPHRAG_EMBED_TIMEOUT_GROWTH_FACTOR = _read_env_float("GRAPHRAG_EMBED_TIMEOUT_GROWTH_FACTOR", 1.5, min_value=1.0)
GRAPHRAG_EMBED_RATE_LIMIT_BACKOFF_MULTIPLIER = _read_env_float(
    "GRAPHRAG_EMBED_RATE_LIMIT_BACKOFF_MULTIPLIER",
    2.0,
    min_value=1.0,
)
GRAPHRAG_EMBED_MODEL_ERROR_BACKOFF_MULTIPLIER = _read_env_float(
    "GRAPHRAG_EMBED_MODEL_ERROR_BACKOFF_MULTIPLIER",
    1.5,
    min_value=1.0,
)
GRAPHRAG_EMBED_ADAPTIVE_SPLIT_AFTER_RETRIES = _read_env_int("GRAPHRAG_EMBED_ADAPTIVE_SPLIT_AFTER_RETRIES", 2, min_value=1)
GRAPHRAG_INDEX_BULK_SIZE = _read_env_int("GRAPHRAG_INDEX_BULK_SIZE", 32, min_value=1)
GRAPHRAG_INDEX_WRITE_TIMEOUT_SECONDS = _read_env_float("GRAPHRAG_INDEX_WRITE_TIMEOUT_SECONDS", 60 * 30, min_value=0.0)
GRAPHRAG_EMBED_QUEUE_SIZE = _read_env_int(
    "GRAPHRAG_EMBED_QUEUE_SIZE",
    max(4, GRAPHRAG_EMBED_CONCURRENCY * 4),
    min_value=1,
)
graphrag_embed_limiter = asyncio.Semaphore(GRAPHRAG_EMBED_CONCURRENCY)


@dataclasses.dataclass
class GraphChange:
    removed_nodes: Set[str] = dataclasses.field(default_factory=set)
    added_updated_nodes: Set[str] = dataclasses.field(default_factory=set)
    removed_edges: Set[Tuple[str, str]] = dataclasses.field(default_factory=set)
    added_updated_edges: Set[Tuple[str, str]] = dataclasses.field(default_factory=set)


@dataclasses.dataclass
class _EmbedRequest:
    index: int
    cache_key: str
    text: str


class GraphRAGEmbeddingBatchError(RuntimeError):
    def __init__(
        self,
        stage: str,
        batch_index: int,
        total_batches: int,
        batch_size: int,
        attempts: int,
        reason: Exception,
    ):
        message = (
            f"[GraphRAGEmbed] stage={stage} failed permanently at batch "
            f"{batch_index + 1}/{total_batches} after {attempts} attempts "
            f"(batch_size={batch_size}): {reason!r}"
        )
        super().__init__(message)
        self.stage = stage
        self.batch_index = batch_index
        self.total_batches = total_batches
        self.batch_size = batch_size
        self.attempts = attempts
        self.reason = reason


def perform_variable_replacements(input: str, history: list[dict] | None = None, variables: dict | None = None) -> str:
    """Perform variable replacements on the input string and in a chat log."""
    if history is None:
        history = []
    if variables is None:
        variables = {}
    result = input

    def replace_all(input: str) -> str:
        result = input
        for k, v in variables.items():
            result = result.replace(f"{{{k}}}", str(v))
        return result

    result = replace_all(result)
    for i, entry in enumerate(history):
        if entry.get("role") == "system":
            entry["content"] = replace_all(entry.get("content") or "")

    return result


def clean_str(input: Any) -> str:
    """Clean an input string by removing HTML escapes, control characters, and other unwanted characters."""
    # If we get non-string input, just give it back
    if not isinstance(input, str):
        return input

    result = html.unescape(input.strip())
    # https://stackoverflow.com/questions/4324790/removing-control-characters-from-a-string-in-python
    return re.sub(r"[\"\x00-\x1f\x7f-\x9f]", "", result)


def dict_has_keys_with_types(data: dict, expected_fields: list[tuple[str, type]]) -> bool:
    """Return True if the given dictionary has the given keys with the given types."""
    for field, field_type in expected_fields:
        if field not in data:
            return False

        value = data[field]
        if not isinstance(value, field_type):
            return False
    return True


def get_llm_cache(llmnm, txt, history, genconf):
    hasher = xxhash.xxh64()
    hasher.update((str(llmnm)+str(txt)+str(history)+str(genconf)).encode("utf-8"))

    k = hasher.hexdigest()
    bin = REDIS_CONN.get(k)
    if not bin:
        return None
    return bin


def set_llm_cache(llmnm, txt, v, history, genconf):
    hasher = xxhash.xxh64()
    hasher.update((str(llmnm)+str(txt)+str(history)+str(genconf)).encode("utf-8"))
    k = hasher.hexdigest()
    REDIS_CONN.set(k, v.encode("utf-8"), 24 * 3600)


def get_embed_cache(llmnm, txt):
    hasher = xxhash.xxh64()
    hasher.update(str(llmnm).encode("utf-8"))
    hasher.update(str(txt).encode("utf-8"))

    k = hasher.hexdigest()
    bin = REDIS_CONN.get(k)
    if not bin:
        return
    return np.array(json.loads(bin))


def set_embed_cache(llmnm, txt, arr):
    hasher = xxhash.xxh64()
    hasher.update(str(llmnm).encode("utf-8"))
    hasher.update(str(txt).encode("utf-8"))

    k = hasher.hexdigest()
    arr = json.dumps(arr.tolist() if isinstance(arr, np.ndarray) else arr)
    REDIS_CONN.set(k, arr.encode("utf-8"), 24 * 3600)


def get_tags_from_cache(kb_ids):
    hasher = xxhash.xxh64()
    hasher.update(str(kb_ids).encode("utf-8"))

    k = hasher.hexdigest()
    bin = REDIS_CONN.get(k)
    if not bin:
        return
    return bin


def set_tags_to_cache(kb_ids, tags):
    hasher = xxhash.xxh64()
    hasher.update(str(kb_ids).encode("utf-8"))

    k = hasher.hexdigest()
    REDIS_CONN.set(k, json.dumps(tags).encode("utf-8"), 600)


def tidy_graph(graph: nx.Graph, callback, check_attribute: bool = True):
    """
    Ensure all nodes and edges in the graph have some essential attribute.
    """

    def is_valid_item(node_attrs: dict) -> bool:
        valid_node = True
        for attr in ["description", "source_id"]:
            if attr not in node_attrs:
                valid_node = False
                break
        return valid_node

    if check_attribute:
        purged_nodes = []
        for node, node_attrs in graph.nodes(data=True):
            if not is_valid_item(node_attrs):
                purged_nodes.append(node)
        for node in purged_nodes:
            graph.remove_node(node)
        if purged_nodes and callback:
            callback(msg=f"Purged {len(purged_nodes)} nodes from graph due to missing essential attributes.")

    purged_edges = []
    for source, target, attr in graph.edges(data=True):
        if check_attribute:
            if not is_valid_item(attr):
                purged_edges.append((source, target))
        if "keywords" not in attr:
            attr["keywords"] = []
    for source, target in purged_edges:
        graph.remove_edge(source, target)
    if purged_edges and callback:
        callback(msg=f"Purged {len(purged_edges)} edges from graph due to missing essential attributes.")


def get_from_to(node1, node2):
    if node1 < node2:
        return (node1, node2)
    else:
        return (node2, node1)


def graph_merge(g1: nx.Graph, g2: nx.Graph, change: GraphChange):
    """Merge graph g2 into g1 in place."""
    for node_name, attr in g2.nodes(data=True):
        change.added_updated_nodes.add(node_name)
        if not g1.has_node(node_name):
            g1.add_node(node_name, **attr)
            continue
        node = g1.nodes[node_name]
        node["description"] += GRAPH_FIELD_SEP + attr["description"]
        # A node's source_id indicates which chunks it came from.
        node["source_id"] += attr["source_id"]

    for source, target, attr in g2.edges(data=True):
        change.added_updated_edges.add(get_from_to(source, target))
        edge = g1.get_edge_data(source, target)
        if edge is None:
            g1.add_edge(source, target, **attr)
            continue
        edge["weight"] += attr.get("weight", 0)
        edge["description"] += GRAPH_FIELD_SEP + attr["description"]
        edge["keywords"] += attr["keywords"]
        # A edge's source_id indicates which chunks it came from.
        edge["source_id"] += attr["source_id"]

    for node_degree in g1.degree:
        g1.nodes[str(node_degree[0])]["rank"] = int(node_degree[1])
    # A graph's source_id indicates which documents it came from.
    if "source_id" not in g1.graph:
        g1.graph["source_id"] = []
    g1.graph["source_id"] += g2.graph.get("source_id", [])
    return g1


def compute_args_hash(*args):
    return md5(str(args).encode()).hexdigest()


def handle_single_entity_extraction(
    record_attributes: list[str],
    chunk_key: str,
):
    if len(record_attributes) < 4 or record_attributes[0] != '"entity"':
        return None
    # add this record as a node in the G
    entity_name = clean_str(record_attributes[1].upper())
    if not entity_name.strip():
        return None
    entity_type = clean_str(record_attributes[2].upper())
    entity_description = clean_str(record_attributes[3])
    entity_source_id = chunk_key
    return dict(
        entity_name=entity_name.upper(),
        entity_type=entity_type.upper(),
        description=entity_description,
        source_id=entity_source_id,
    )


def handle_single_relationship_extraction(record_attributes: list[str], chunk_key: str):
    if len(record_attributes) < 5 or record_attributes[0] != '"relationship"':
        return None
    # add this record as edge
    source = clean_str(record_attributes[1].upper())
    target = clean_str(record_attributes[2].upper())
    edge_description = clean_str(record_attributes[3])

    edge_keywords = clean_str(record_attributes[4])
    edge_source_id = chunk_key
    weight = float(record_attributes[-1]) if is_float_regex(record_attributes[-1]) else 1.0
    pair = sorted([source.upper(), target.upper()])
    return dict(
        src_id=pair[0],
        tgt_id=pair[1],
        weight=weight,
        description=edge_description,
        keywords=edge_keywords,
        source_id=edge_source_id,
        metadata={"created_at": time.time()},
    )


def pack_user_ass_to_openai_messages(*args: str):
    roles = ["user", "assistant"]
    return [{"role": roles[i % 2], "content": content} for i, content in enumerate(args)]


def split_string_by_multi_markers(content: str, markers: list[str]) -> list[str]:
    """Split a string by multiple markers"""
    if not markers:
        return [content]
    results = re.split("|".join(re.escape(marker) for marker in markers), content)
    return [r.strip() for r in results if r.strip()]


def is_float_regex(value):
    return bool(re.match(r"^[-+]?[0-9]*\.?[0-9]+$", value))


def chunk_id(chunk):
    return xxhash.xxh64((chunk["content_with_weight"] + chunk["kb_id"]).encode("utf-8")).hexdigest()


def _embedding_error_kind(exc: Exception) -> str:
    message = str(exc).lower()

    hard_markers = [
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
        "shape mismatch",
        "output size mismatch",
        "invalid input",
        "permanent",
    ]
    if any(marker in message for marker in hard_markers):
        return "hard_config"

    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return "timeout"
    if isinstance(exc, (ConnectionError, OSError)):
        return "connection"

    if any(marker in message for marker in ("rate limit", "too many request", "quota", " 429", "status 429")):
        return "rate_limit"

    if "model" in message and any(
        marker in message
        for marker in (
            "busy",
            "overload",
            "overloaded",
            "temporar",
            "timeout",
            "timed out",
            "try again",
            "retry",
            "service unavailable",
            "internal",
        )
    ):
        return "model_retryable"

    if any(
        marker in message
        for marker in (
            "service unavailable",
            "bad gateway",
            "gateway timeout",
            "internalservererror",
            "internal server error",
            " 500",
            " 502",
            " 503",
            " 504",
            "status 500",
            "status 502",
            "status 503",
            "status 504",
        )
    ):
        return "service"

    if any(
        marker in message
        for marker in (
            "connection reset",
            "connection aborted",
            "connection refused",
            "server disconnected",
            "api connection",
        )
    ):
        return "connection"

    if any(
        marker in message
        for marker in (
            "timeout",
            "timed out",
        )
    ):
        return "timeout"

    transient_markers = [
        "timeout",
        "timed out",
        "temporar",
        "retry",
        "try again",
    ]
    if any(marker in message for marker in transient_markers):
        return "transient"
    return "hard_config"


def _is_transient_embedding_error(exc: Exception) -> bool:
    return _embedding_error_kind(exc) != "hard_config"


def _should_split_embedding_batch(error_kind: str) -> bool:
    return error_kind in {"timeout", "service", "connection", "model_retryable", "transient"}


def _backoff_multiplier_for_embedding_error(error_kind: str) -> float:
    if error_kind == "rate_limit":
        return GRAPHRAG_EMBED_RATE_LIMIT_BACKOFF_MULTIPLIER
    if error_kind == "model_retryable":
        return GRAPHRAG_EMBED_MODEL_ERROR_BACKOFF_MULTIPLIER
    return 1.0


def _normalize_embedding_vectors(vectors, expected_size: int):
    if isinstance(vectors, np.ndarray):
        arr = vectors
        if arr.ndim == 1:
            if expected_size != 1:
                raise ValueError(
                    f"embedding output shape mismatch: expected {expected_size} vectors but got a 1D array."
                )
            return [arr]
        if arr.shape[0] != expected_size:
            raise ValueError(
                f"embedding output size mismatch: expected {expected_size} vectors but got {arr.shape[0]}."
            )
        return [arr[i] for i in range(arr.shape[0])]

    if isinstance(vectors, list):
        if len(vectors) != expected_size:
            raise ValueError(
                f"embedding output size mismatch: expected {expected_size} vectors but got {len(vectors)}."
            )
        return vectors

    raise TypeError(f"unsupported embedding output type: {type(vectors)!r}")


def _retry_limit_label(max_retries: int) -> str:
    return "unlimited" if max_retries <= 0 else str(max_retries)


async def _encode_batch_with_retry(
    *,
    embd_mdl,
    stage: str,
    batch_index: int,
    total_batches: int,
    batch_requests: list[_EmbedRequest],
    callback,
):
    assert batch_requests, "batch_requests must not be empty"

    batch_texts = [request.text for request in batch_requests]
    batch_size = len(batch_texts)
    max_retries = GRAPHRAG_EMBED_MAX_RETRIES
    base_backoff = GRAPHRAG_EMBED_RETRY_BASE_SECONDS
    max_backoff = GRAPHRAG_EMBED_RETRY_MAX_SECONDS
    attempt_timeout = GRAPHRAG_EMBED_ATTEMPT_TIMEOUT_SECONDS
    max_attempt_timeout = GRAPHRAG_EMBED_MAX_ATTEMPT_TIMEOUT_SECONDS
    split_after = GRAPHRAG_EMBED_ADAPTIVE_SPLIT_AFTER_RETRIES
    loop = asyncio.get_running_loop()
    current_attempt_timeout = attempt_timeout

    last_error: Exception | None = None
    attempts_used = 0
    attempt = 0
    while True:
        attempt += 1
        attempts_used = attempt
        started = loop.time()
        try:
            async with graphrag_embed_limiter:
                encode_task = thread_pool_exec(embd_mdl.encode, batch_texts)
                if current_attempt_timeout > 0:
                    vectors, _ = await asyncio.wait_for(encode_task, timeout=current_attempt_timeout)
                else:
                    vectors, _ = await encode_task
            normalized_vectors = _normalize_embedding_vectors(vectors, batch_size)
            elapsed = loop.time() - started
            logging.info(
                (
                    "[GraphRAGEmbed] stage=%s batch=%d/%d attempt=%d size=%d "
                    "elapsed=%.2fs result=success"
                ),
                stage,
                batch_index + 1,
                total_batches,
                attempt,
                batch_size,
                elapsed,
            )
            return normalized_vectors
        except Exception as exc:  # noqa: PERF203
            elapsed = loop.time() - started
            last_error = exc
            error_kind = _embedding_error_kind(exc)
            transient = error_kind != "hard_config"
            logging.warning(
                (
                    "[GraphRAGEmbed] stage=%s batch=%d/%d attempt=%d/%s size=%d "
                    "elapsed=%.2fs transient=%s kind=%s timeout=%.2fs reason=%r"
                ),
                stage,
                batch_index + 1,
                total_batches,
                attempt,
                _retry_limit_label(max_retries),
                batch_size,
                elapsed,
                transient,
                error_kind,
                current_attempt_timeout,
                exc,
            )
            if (
                transient
                and batch_size > 1
                and attempt >= split_after
                and _should_split_embedding_batch(error_kind)
            ):
                mid = batch_size // 2
                if callback:
                    callback(
                        msg=(
                            f"[GraphRAGEmbed] adaptive split {stage} batch {batch_index + 1}/{total_batches} "
                            f"size {batch_size} -> {mid}+{batch_size - mid} after {attempt} attempts "
                            f"(kind={error_kind}, reason={exc!r})"
                        )
                    )
                left_vectors = await _encode_batch_with_retry(
                    embd_mdl=embd_mdl,
                    stage=stage,
                    batch_index=batch_index,
                    total_batches=total_batches,
                    batch_requests=batch_requests[:mid],
                    callback=callback,
                )
                right_vectors = await _encode_batch_with_retry(
                    embd_mdl=embd_mdl,
                    stage=stage,
                    batch_index=batch_index,
                    total_batches=total_batches,
                    batch_requests=batch_requests[mid:],
                    callback=callback,
                )
                return left_vectors + right_vectors

            attempts_exhausted = max_retries > 0 and attempt >= max_retries
            if (not transient) or attempts_exhausted:
                break

            timeout_msg = ""
            if error_kind == "timeout" and current_attempt_timeout > 0:
                next_timeout = current_attempt_timeout * GRAPHRAG_EMBED_TIMEOUT_GROWTH_FACTOR
                if max_attempt_timeout > 0:
                    next_timeout = min(max_attempt_timeout, next_timeout)
                if next_timeout > current_attempt_timeout:
                    timeout_msg = f", timeout {current_attempt_timeout:.2f}s -> {next_timeout:.2f}s"
                    current_attempt_timeout = next_timeout

            delay = min(max_backoff, base_backoff * (2 ** (attempt - 1))) if base_backoff > 0 else 0.0
            delay *= _backoff_multiplier_for_embedding_error(error_kind)
            delay = min(max_backoff, delay) if max_backoff > 0 else delay
            jitter = random.uniform(0, max(0.5, delay * 0.2)) if delay > 0 else random.uniform(0.0, 0.3)
            wait_seconds = delay + jitter
            if callback:
                callback(
                    msg=(
                        f"[GraphRAGEmbed] retry {stage} batch {batch_index + 1}/{total_batches} "
                        f"attempt {attempt + 1}/{_retry_limit_label(max_retries)} in {wait_seconds:.2f}s "
                        f"(size={batch_size}, kind={error_kind}{timeout_msg}, reason={exc!r})"
                    )
                )
            await asyncio.sleep(wait_seconds)

    if last_error is None:
        last_error = RuntimeError("embedding batch failed without explicit exception")
    raise GraphRAGEmbeddingBatchError(
        stage=stage,
        batch_index=batch_index,
        total_batches=total_batches,
        batch_size=batch_size,
        attempts=attempts_used or max_retries,
        reason=last_error,
    )


async def _embed_requests_with_bounded_workers(
    *,
    stage: str,
    embd_mdl,
    requests: list[_EmbedRequest],
    callback,
    progress_start: float | None = None,
    progress_end: float | None = None,
):
    total_items = len(requests)
    if total_items == 0:
        return []

    results = [None] * total_items
    miss_requests: list[_EmbedRequest] = []
    for request in requests:
        cached_vec = get_embed_cache(embd_mdl.llm_name, request.cache_key)
        if cached_vec is not None:
            results[request.index] = cached_vec
        else:
            miss_requests.append(request)

    total_miss = len(miss_requests)
    if total_miss == 0:
        if callback:
            callback(msg=f"Get embedding of {stage}: {total_items}/{total_items}, batches 0/0")
        return results

    batch_size = GRAPHRAG_EMBED_BATCH_SIZE
    batches: list[list[_EmbedRequest]] = [
        miss_requests[i : i + batch_size] for i in range(0, total_miss, batch_size)
    ]
    total_batches = len(batches)
    worker_count = min(GRAPHRAG_EMBED_CONCURRENCY, total_batches)
    queue = asyncio.Queue(maxsize=GRAPHRAG_EMBED_QUEUE_SIZE)
    progress_lock = asyncio.Lock()
    completed_items = total_items - total_miss
    completed_batches = 0

    def emit_progress(msg: str, current_items: int | None = None):
        if not callback:
            return
        kwargs = {"msg": msg}
        if (
            progress_start is not None
            and progress_end is not None
            and current_items is not None
            and total_items > 0
        ):
            ratio = max(0.0, min(1.0, current_items / total_items))
            kwargs["prog"] = progress_start + (progress_end - progress_start) * ratio
        callback(**kwargs)

    if callback and completed_items > 0:
        emit_progress(
            msg=(
                f"Get embedding of {stage}: {completed_items}/{total_items}, "
                f"batches {completed_batches}/{total_batches}"
            ),
            current_items=completed_items,
        )

    async def producer():
        for batch_index, batch in enumerate(batches):
            await queue.put((batch_index, batch))
        for _ in range(worker_count):
            await queue.put(None)

    async def worker(worker_id: int):
        nonlocal completed_items, completed_batches
        while True:
            queued = await queue.get()
            if queued is None:
                queue.task_done()
                return

            batch_index, batch = queued
            try:
                embedded = await _encode_batch_with_retry(
                    embd_mdl=embd_mdl,
                    stage=stage,
                    batch_index=batch_index,
                    total_batches=total_batches,
                    batch_requests=batch,
                    callback=callback,
                )
                for local_idx, request in enumerate(batch):
                    vector = embedded[local_idx]
                    results[request.index] = vector
                    set_embed_cache(embd_mdl.llm_name, request.cache_key, vector)

                async with progress_lock:
                    completed_items += len(batch)
                    completed_batches += 1
                    current_items = completed_items
                    current_batches = completed_batches

                if callback:
                    emit_progress(
                        msg=(
                            f"Get embedding of {stage}: {current_items}/{total_items}, "
                            f"batches {current_batches}/{total_batches}"
                        ),
                        current_items=current_items,
                    )
            except Exception as exc:
                logging.error(
                    "[GraphRAGEmbed] worker=%d stage=%s batch=%d/%d failed: %r",
                    worker_id,
                    stage,
                    batch_index + 1,
                    total_batches,
                    exc,
                )
                raise
            finally:
                queue.task_done()

    producer_task = asyncio.create_task(producer())
    worker_tasks = [asyncio.create_task(worker(idx)) for idx in range(worker_count)]

    try:
        await asyncio.gather(producer_task, *worker_tasks, return_exceptions=False)
    except Exception:
        producer_task.cancel()
        for worker_task in worker_tasks:
            worker_task.cancel()
        await asyncio.gather(producer_task, *worker_tasks, return_exceptions=True)
        raise

    for idx, vector in enumerate(results):
        if vector is None:
            raise RuntimeError(f"embedding vector missing for {stage} request at index {idx}")

    return results


async def graph_node_to_chunk(kb_id, embd_mdl, ent_name, meta, chunks):
    global chat_limiter
    enable_timeout_assertion = os.environ.get("ENABLE_TIMEOUT_ASSERTION")
    chunk = {
        "id": get_uuid(),
        "important_kwd": [ent_name],
        "title_tks": rag_tokenizer.tokenize(ent_name),
        "entity_kwd": ent_name,
        "knowledge_graph_kwd": "entity",
        "entity_type_kwd": meta["entity_type"],
        "content_with_weight": json.dumps(meta, ensure_ascii=False),
        "content_ltks": rag_tokenizer.tokenize(meta["description"]),
        "source_id": meta["source_id"],
        "kb_id": kb_id,
        "available_int": 0,
    }
    chunk["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(chunk["content_ltks"])
    ebd = get_embed_cache(embd_mdl.llm_name, ent_name)
    if ebd is None:
        async with chat_limiter:
            timeout = 3 if enable_timeout_assertion else 30000000
            ebd, _ = await asyncio.wait_for(
                thread_pool_exec(embd_mdl.encode, [ent_name]),
                timeout=timeout
            )
        ebd = ebd[0]
        set_embed_cache(embd_mdl.llm_name, ent_name, ebd)
    assert ebd is not None
    chunk["q_%d_vec" % len(ebd)] = ebd
    chunks.append(chunk)


@timeout(3, 3)
async def get_relation(tenant_id, kb_id, from_ent_name, to_ent_name, size=1):
    ents = from_ent_name
    if isinstance(ents, str):
        ents = [from_ent_name]
    if isinstance(to_ent_name, str):
        to_ent_name = [to_ent_name]
    ents.extend(to_ent_name)
    ents = list(set(ents))
    conds = {"fields": ["content_with_weight"], "size": size, "from_entity_kwd": ents, "to_entity_kwd": ents, "knowledge_graph_kwd": ["relation"]}
    res = []
    es_res = await settings.retriever.search(conds, search.index_name(tenant_id), [kb_id] if isinstance(kb_id, str) else kb_id)
    for id in es_res.ids:
        try:
            if size == 1:
                return json.loads(es_res.field[id]["content_with_weight"])
            res.append(json.loads(es_res.field[id]["content_with_weight"]))
        except Exception:
            continue
    return res


async def graph_edge_to_chunk(kb_id, embd_mdl, from_ent_name, to_ent_name, meta, chunks):
    enable_timeout_assertion = os.environ.get("ENABLE_TIMEOUT_ASSERTION")
    chunk = {
        "id": get_uuid(),
        "from_entity_kwd": from_ent_name,
        "to_entity_kwd": to_ent_name,
        "knowledge_graph_kwd": "relation",
        "content_with_weight": json.dumps(meta, ensure_ascii=False),
        "content_ltks": rag_tokenizer.tokenize(meta["description"]),
        "important_kwd": meta["keywords"],
        "source_id": meta["source_id"],
        "weight_int": int(meta["weight"]),
        "kb_id": kb_id,
        "available_int": 0,
    }
    chunk["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(chunk["content_ltks"])
    txt = f"{from_ent_name}->{to_ent_name}"
    ebd = get_embed_cache(embd_mdl.llm_name, txt)
    if ebd is None:
        async with chat_limiter:
            timeout = 3 if enable_timeout_assertion else 300000000
            ebd, _ = await asyncio.wait_for(
                thread_pool_exec(
                    embd_mdl.encode,
                    [txt + f": {meta['description']}"]
                ),
                timeout=timeout
            )
        ebd = ebd[0]
        set_embed_cache(embd_mdl.llm_name, txt, ebd)
    assert ebd is not None
    chunk["q_%d_vec" % len(ebd)] = ebd
    chunks.append(chunk)


async def does_graph_contains(tenant_id, kb_id, doc_id):
    # Get doc_ids of graph
    fields = ["source_id"]
    condition = {
        "knowledge_graph_kwd": ["graph"],
        "removed_kwd": "N",
    }
    res = await thread_pool_exec(
        settings.docStoreConn.search,
        fields, [], condition, [], OrderByExpr(),
        0, 1, search.index_name(tenant_id), [kb_id]
    )
    fields2 = settings.docStoreConn.get_fields(res, fields)
    graph_doc_ids = set()
    for chunk_id in fields2.keys():
        graph_doc_ids = set(fields2[chunk_id]["source_id"])
    return doc_id in graph_doc_ids


async def get_graph_doc_ids(tenant_id, kb_id) -> list[str]:
    conds = {"fields": ["source_id"], "removed_kwd": "N", "size": 1, "knowledge_graph_kwd": ["graph"]}
    res = await settings.retriever.search(conds, search.index_name(tenant_id), [kb_id])
    doc_ids = []
    if res.total == 0:
        return doc_ids
    for id in res.ids:
        doc_ids = res.field[id]["source_id"]
    return doc_ids


async def get_subgraphs_by_doc_ids(tenant_id, kb_id, doc_ids) -> dict[str, nx.Graph]:
    """Load persisted per-document subgraphs for resumable GraphRAG runs."""
    wanted = set(doc_ids or [])
    if not wanted:
        return {}

    flds = ["knowledge_graph_kwd", "content_with_weight", "source_id", "removed_kwd"]
    result: dict[str, nx.Graph] = {}
    bs = 256
    for offset in range(0, 1024 * bs, bs):
        es_res = await thread_pool_exec(
            settings.docStoreConn.search,
            flds,
            [],
            {"kb_id": kb_id, "knowledge_graph_kwd": ["subgraph"], "removed_kwd": "N"},
            [],
            OrderByExpr(),
            offset,
            bs,
            search.index_name(tenant_id),
            [kb_id],
        )
        es_res = settings.docStoreConn.get_fields(es_res, flds)
        if not es_res:
            break

        for d in es_res.values():
            if d.get("knowledge_graph_kwd") != "subgraph":
                continue
            source_ids = d.get("source_id") or []
            if isinstance(source_ids, str):
                source_ids = [source_ids]
            matched_doc_ids = wanted.intersection(source_ids)
            if not matched_doc_ids:
                continue
            try:
                graph = json_graph.node_link_graph(json.loads(d["content_with_weight"]), edges="edges")
            except Exception as exc:
                logging.warning("Failed to load persisted subgraph for kb %s: %s", kb_id, exc)
                continue
            if "source_id" not in graph.graph:
                graph.graph["source_id"] = list(source_ids)
            for doc_id in matched_doc_ids:
                result[doc_id] = graph
        if set(result) >= wanted:
            break
    return result


async def get_graph(tenant_id, kb_id, exclude_rebuild=None):
    conds = {"fields": ["content_with_weight", "removed_kwd", "source_id"], "size": 1, "knowledge_graph_kwd": ["graph"]}
    res = await settings.retriever.search(conds, search.index_name(tenant_id), [kb_id])
    if not res.total == 0:
        for id in res.ids:
            try:
                if res.field[id]["removed_kwd"] == "N":
                    g = json_graph.node_link_graph(json.loads(res.field[id]["content_with_weight"]), edges="edges")
                    if "source_id" not in g.graph:
                        g.graph["source_id"] = res.field[id]["source_id"]
                else:
                    g = await rebuild_graph(tenant_id, kb_id, exclude_rebuild)
                return g
            except Exception:
                continue
    result = None
    return result


async def set_graph(
    tenant_id: str,
    kb_id: str,
    embd_mdl,
    graph: nx.Graph,
    change: GraphChange,
    callback,
    progress_start: float | None = None,
    progress_end: float | None = None,
):
    start = asyncio.get_running_loop().time()
    progress_span = None
    if progress_start is not None and progress_end is not None:
        progress_span = max(0.0, progress_end - progress_start)

    def progress_at(ratio: float) -> float | None:
        if progress_span is None:
            return None
        return progress_start + progress_span * max(0.0, min(1.0, ratio))

    def callback_with_progress(msg: str, ratio: float | None = None):
        if not callback:
            return
        kwargs = {"msg": msg}
        if ratio is not None:
            prog = progress_at(ratio)
            if prog is not None:
                kwargs["prog"] = prog
        callback(**kwargs)

    chunks = [
        {
            "id": get_uuid(),
            "content_with_weight": json.dumps(nx.node_link_data(graph, edges="edges"), ensure_ascii=False),
            "knowledge_graph_kwd": "graph",
            "kb_id": kb_id,
            "source_id": graph.graph.get("source_id", []),
            "available_int": 0,
            "removed_kwd": "N",
        }
    ]

    # generate updated subgraphs
    for source in graph.graph["source_id"]:
        subgraph = graph.subgraph([n for n in graph.nodes if source in graph.nodes[n]["source_id"]]).copy()
        subgraph.graph["source_id"] = [source]
        for n in subgraph.nodes:
            subgraph.nodes[n]["source_id"] = [source]
        chunks.append(
            {
                "id": get_uuid(),
                "content_with_weight": json.dumps(nx.node_link_data(subgraph, edges="edges"), ensure_ascii=False),
                "knowledge_graph_kwd": "subgraph",
                "kb_id": kb_id,
                "source_id": [source],
                "available_int": 0,
                "removed_kwd": "N",
            }
        )

    node_chunks = []
    node_requests = []
    node_order = sorted(change.added_updated_nodes)
    for idx, node in enumerate(node_order):
        node_attrs = graph.nodes[node]
        node_chunk = {
            "id": get_uuid(),
            "important_kwd": [node],
            "title_tks": rag_tokenizer.tokenize(node),
            "entity_kwd": node,
            "knowledge_graph_kwd": "entity",
            "entity_type_kwd": node_attrs["entity_type"],
            "content_with_weight": json.dumps(node_attrs, ensure_ascii=False),
            "content_ltks": rag_tokenizer.tokenize(node_attrs["description"]),
            "source_id": node_attrs["source_id"],
            "kb_id": kb_id,
            "available_int": 0,
        }
        node_chunk["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(node_chunk["content_ltks"])
        node_chunks.append(node_chunk)
        node_requests.append(_EmbedRequest(index=idx, cache_key=node, text=node))

    node_vectors = []
    if node_requests:
        try:
            node_vectors = await _embed_requests_with_bounded_workers(
                stage="nodes",
                embd_mdl=embd_mdl,
                requests=node_requests,
                callback=callback,
                progress_start=progress_at(0.00),
                progress_end=progress_at(0.55),
            )
        except Exception as exc:
            if callback:
                callback(
                    msg=(
                        "[GraphRAGEmbed] nodes embedding failed after retries. "
                        "Task is resumable; please use Resume after tuning batch/concurrency/timeout."
                    )
                )
            raise exc

    for idx, vector in enumerate(node_vectors):
        node_chunks[idx]["q_%d_vec" % len(vector)] = vector
    chunks.extend(node_chunks)

    edge_chunks = []
    edge_requests = []
    edge_pairs = sorted(change.added_updated_edges)
    for pair in edge_pairs:
        from_node, to_node = pair
        edge_attrs = graph.get_edge_data(from_node, to_node)
        if not edge_attrs:
            continue
        edge_chunk = {
            "id": get_uuid(),
            "from_entity_kwd": from_node,
            "to_entity_kwd": to_node,
            "knowledge_graph_kwd": "relation",
            "content_with_weight": json.dumps(edge_attrs, ensure_ascii=False),
            "content_ltks": rag_tokenizer.tokenize(edge_attrs["description"]),
            "important_kwd": edge_attrs["keywords"],
            "source_id": edge_attrs["source_id"],
            "weight_int": int(edge_attrs["weight"]),
            "kb_id": kb_id,
            "available_int": 0,
        }
        edge_chunk["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(edge_chunk["content_ltks"])
        edge_chunks.append(edge_chunk)
        relation_key = f"{from_node}->{to_node}"
        edge_requests.append(
            _EmbedRequest(
                index=len(edge_requests),
                cache_key=relation_key,
                text=relation_key + f": {edge_attrs['description']}",
            )
        )

    edge_vectors = []
    if edge_requests:
        try:
            edge_vectors = await _embed_requests_with_bounded_workers(
                stage="edges",
                embd_mdl=embd_mdl,
                requests=edge_requests,
                callback=callback,
                progress_start=progress_at(0.55),
                progress_end=progress_at(0.85),
            )
        except Exception as exc:
            if callback:
                callback(
                    msg=(
                        "[GraphRAGEmbed] edges embedding failed after retries. "
                        "Task is resumable; please use Resume after tuning batch/concurrency/timeout."
                    )
                )
            raise exc

    for idx, vector in enumerate(edge_vectors):
        edge_chunks[idx]["q_%d_vec" % len(vector)] = vector
    chunks.extend(edge_chunks)

    now = asyncio.get_running_loop().time()
    callback_with_progress(f"set_graph converted graph change to {len(chunks)} chunks in {now - start:.2f}s.", 0.85)
    start = now

    # Generate all LLM/vector-dependent chunks before deleting the old graph.
    # This keeps a resumable graph available if quota/timeout errors happen above.
    await thread_pool_exec(
        settings.docStoreConn.delete,
        {"knowledge_graph_kwd": ["graph", "subgraph"]},
        search.index_name(tenant_id),
        kb_id
    )

    if change.removed_nodes:
        await thread_pool_exec(
            settings.docStoreConn.delete,
            {"knowledge_graph_kwd": ["entity"], "entity_kwd": sorted(change.removed_nodes)},
            search.index_name(tenant_id),
            kb_id
        )

    if change.removed_edges:

        async def del_edges(from_node, to_node):
            async with chat_limiter:
                await thread_pool_exec(
                    settings.docStoreConn.delete,
                    {"knowledge_graph_kwd": ["relation"], "from_entity_kwd": from_node, "to_entity_kwd": to_node},
                    search.index_name(tenant_id),
                    kb_id
                )

        tasks = []
        for from_node, to_node in change.removed_edges:
            tasks.append(asyncio.create_task(del_edges(from_node, to_node)))

        try:
            await asyncio.gather(*tasks, return_exceptions=False)
        except Exception as e:
            logging.error(f"Error while deleting edges: {e}")
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

    now = asyncio.get_running_loop().time()
    callback_with_progress(
        f"set_graph removed {len(change.removed_nodes)} nodes and {len(change.removed_edges)} edges from index in {now - start:.2f}s.",
        0.88,
    )
    start = now

    es_bulk_size = GRAPHRAG_INDEX_BULK_SIZE
    for b in range(0, len(chunks), es_bulk_size):
        insert_task = thread_pool_exec(
            settings.docStoreConn.insert,
            chunks[b : b + es_bulk_size],
            search.index_name(tenant_id),
            kb_id
        )
        if GRAPHRAG_INDEX_WRITE_TIMEOUT_SECONDS > 0:
            doc_store_result = await asyncio.wait_for(
                insert_task,
                timeout=GRAPHRAG_INDEX_WRITE_TIMEOUT_SECONDS,
            )
        else:
            doc_store_result = await insert_task
        if b % (es_bulk_size * 25) == 0:
            inserted = min(b + es_bulk_size, len(chunks))
            insert_ratio = 0.88 + 0.12 * (inserted / max(len(chunks), 1))
            callback_with_progress(f"Insert chunks: {inserted}/{len(chunks)}", insert_ratio)
        if doc_store_result:
            error_message = f"Insert chunk error: {doc_store_result}, please check log file and Elasticsearch/Infinity status!"
            raise Exception(error_message)
    now = asyncio.get_running_loop().time()
    callback_with_progress(
        f"set_graph added/updated {len(change.added_updated_nodes)} nodes and {len(change.added_updated_edges)} edges from index in {now - start:.2f}s.",
        1.0,
    )


def is_continuous_subsequence(subseq, seq):
    def find_all_indexes(tup, value):
        indexes = []
        start = 0
        while True:
            try:
                index = tup.index(value, start)
                indexes.append(index)
                start = index + 1
            except ValueError:
                break
        return indexes

    index_list = find_all_indexes(seq, subseq[0])
    for idx in index_list:
        if idx != len(seq) - 1:
            if seq[idx + 1] == subseq[-1]:
                return True
    return False


def merge_tuples(list1, list2):
    result = []
    for tup in list1:
        last_element = tup[-1]
        if last_element in tup[:-1]:
            result.append(tup)
        else:
            matching_tuples = [t for t in list2 if t[0] == last_element]
            already_match_flag = 0
            for match in matching_tuples:
                matchh = (match[1], match[0])
                if is_continuous_subsequence(match, tup) or is_continuous_subsequence(matchh, tup):
                    continue
                already_match_flag = 1
                merged_tuple = tup + match[1:]
                result.append(merged_tuple)
            if not already_match_flag:
                result.append(tup)
    return result


async def get_entity_type2samples(idxnms, kb_ids: list):
    es_res = await settings.retriever.search({"knowledge_graph_kwd": "ty2ents", "kb_id": kb_ids, "size": 10000, "fields": ["content_with_weight"]},idxnms,kb_ids)

    res = defaultdict(list)
    for id in es_res.ids:
        smp = es_res.field[id].get("content_with_weight")
        if not smp:
            continue
        try:
            smp = json.loads(smp)
        except Exception as e:
            logging.exception(e)

        for ty, ents in smp.items():
            res[ty].extend(ents)
    return res


def flat_uniq_list(arr, key):
    res = []
    for a in arr:
        a = a[key]
        if isinstance(a, list):
            res.extend(a)
        else:
            res.append(a)
    return list(set(res))


async def rebuild_graph(tenant_id, kb_id, exclude_rebuild=None):
    graph = nx.Graph()
    flds = ["knowledge_graph_kwd", "content_with_weight", "source_id"]
    bs = 256
    for i in range(0, 1024 * bs, bs):
        es_res = await thread_pool_exec(
            settings.docStoreConn.search,
            flds, [], {"kb_id": kb_id, "knowledge_graph_kwd": ["subgraph"]},
            [], OrderByExpr(), i, bs, search.index_name(tenant_id), [kb_id]
        )
        # tot = settings.docStoreConn.get_total(es_res)
        es_res = settings.docStoreConn.get_fields(es_res, flds)

        if len(es_res) == 0:
            break

        for id, d in es_res.items():
            assert d["knowledge_graph_kwd"] == "subgraph"
            if isinstance(exclude_rebuild, list):
                if sum([n in d["source_id"] for n in exclude_rebuild]):
                    continue
            elif exclude_rebuild in d["source_id"]:
                continue

            next_graph = json_graph.node_link_graph(json.loads(d["content_with_weight"]), edges="edges")
            merged_graph = nx.compose(graph, next_graph)
            merged_source = {n: graph.nodes[n]["source_id"] + next_graph.nodes[n]["source_id"] for n in graph.nodes & next_graph.nodes}
            nx.set_node_attributes(merged_graph, merged_source, "source_id")
            if "source_id" in graph.graph:
                merged_graph.graph["source_id"] = graph.graph["source_id"] + next_graph.graph["source_id"]
            else:
                merged_graph.graph["source_id"] = next_graph.graph["source_id"]
            graph = merged_graph

    if len(graph.nodes) == 0:
        return None
    graph.graph["source_id"] = sorted(graph.graph["source_id"])
    return graph
