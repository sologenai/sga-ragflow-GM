#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
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

import math
import hashlib
import asyncio
import sys
import types

import networkx as nx
import numpy as np
import pytest

if "xxhash" not in sys.modules:
    class _FakeXXHash:
        def __init__(self, data=b""):
            self._buf = bytearray()
            if data:
                self.update(data)

        def update(self, data):
            if isinstance(data, str):
                data = data.encode("utf-8")
            self._buf.extend(data)
            return self

        def hexdigest(self):
            return hashlib.sha1(bytes(self._buf)).hexdigest()

    fake_xxhash = types.SimpleNamespace(xxh64=lambda data=b"": _FakeXXHash(data))
    sys.modules["xxhash"] = fake_xxhash

if "quart" not in sys.modules:
    async def _dummy_make_response(payload):
        return payload

    def _dummy_jsonify(payload):
        return payload

    sys.modules["quart"] = types.SimpleNamespace(
        make_response=_dummy_make_response,
        jsonify=_dummy_jsonify,
    )

if "rag.nlp" not in sys.modules:
    fake_rag_tokenizer = types.SimpleNamespace(
        tokenize=lambda txt: txt.split() if isinstance(txt, str) else [],
        fine_grained_tokenize=lambda txt: txt.split() if isinstance(txt, str) else [],
    )
    fake_search = types.SimpleNamespace(index_name=lambda _tenant_id: "idx")
    fake_nlp = types.SimpleNamespace(rag_tokenizer=fake_rag_tokenizer, search=fake_search)
    sys.modules["rag.nlp"] = fake_nlp
    sys.modules["rag.nlp.rag_tokenizer"] = fake_rag_tokenizer
    sys.modules["rag.nlp.search"] = fake_search

if "rag.utils.redis_conn" not in sys.modules:
    class _FakeRedisConn:
        def get(self, *_args, **_kwargs):
            return None

        def set(self, *_args, **_kwargs):
            return None

    sys.modules["rag.utils.redis_conn"] = types.SimpleNamespace(REDIS_CONN=_FakeRedisConn())

if "common.settings" not in sys.modules:
    fake_doc_store_conn = types.SimpleNamespace(delete=lambda *args, **kwargs: None, insert=lambda *args, **kwargs: None)
    fake_retriever = types.SimpleNamespace(search=lambda *args, **kwargs: None)
    fake_settings = types.SimpleNamespace(docStoreConn=fake_doc_store_conn, retriever=fake_retriever)
    sys.modules["common.settings"] = fake_settings

from rag.graphrag import utils as graphrag_utils


class CountingEmbedModel:
    def __init__(self):
        self.llm_name = "mock-embed"
        self.calls = 0
        self.batch_sizes = []
        self._failed_once = set()
        self.fail_once_prefix = None
        self.always_fail = False

    def encode(self, texts):
        self.calls += 1
        self.batch_sizes.append(len(texts))

        if self.always_fail:
            raise ValueError("permanent-invalid-input")

        if self.fail_once_prefix and texts and texts[0].startswith(self.fail_once_prefix):
            if texts[0] not in self._failed_once:
                self._failed_once.add(texts[0])
                raise TimeoutError("temporary-timeout")

        vectors = [[float((len(text) + i) % 11) for i in range(8)] for text in texts]
        return np.array(vectors), len(texts)


async def _direct_thread_pool_exec(func, *args, **kwargs):
    return func(*args, **kwargs)


def _collect_callback(logs):
    def callback(*args, **kwargs):
        msg = kwargs.get("msg")
        if msg:
            logs.append(msg)

    return callback


@pytest.fixture
def configure_embed_pipeline(monkeypatch):
    monkeypatch.setattr(graphrag_utils, "GRAPHRAG_EMBED_BATCH_SIZE", 16, raising=False)
    monkeypatch.setattr(graphrag_utils, "GRAPHRAG_EMBED_CONCURRENCY", 2, raising=False)
    monkeypatch.setattr(graphrag_utils, "GRAPHRAG_EMBED_QUEUE_SIZE", 8, raising=False)
    monkeypatch.setattr(graphrag_utils, "GRAPHRAG_EMBED_MAX_RETRIES", 3, raising=False)
    monkeypatch.setattr(graphrag_utils, "GRAPHRAG_EMBED_RETRY_BASE_SECONDS", 0.001, raising=False)
    monkeypatch.setattr(graphrag_utils, "GRAPHRAG_EMBED_RETRY_MAX_SECONDS", 0.01, raising=False)
    monkeypatch.setattr(graphrag_utils, "graphrag_embed_limiter", asyncio.Semaphore(2), raising=False)
    monkeypatch.setattr(graphrag_utils, "thread_pool_exec", _direct_thread_pool_exec, raising=False)
    monkeypatch.setattr(graphrag_utils, "get_embed_cache", lambda *_args, **_kwargs: None, raising=False)
    monkeypatch.setattr(graphrag_utils, "set_embed_cache", lambda *_args, **_kwargs: None, raising=False)


@pytest.mark.asyncio
async def test_large_scale_batching_reduces_request_count(configure_embed_pipeline):
    model = CountingEmbedModel()
    total_nodes = 32000
    requests = [
        graphrag_utils._EmbedRequest(index=i, cache_key=f"node-{i}", text=f"node-{i}")
        for i in range(total_nodes)
    ]

    vectors = await graphrag_utils._embed_requests_with_bounded_workers(
        stage="nodes",
        embd_mdl=model,
        requests=requests,
        callback=None,
    )

    assert len(vectors) == total_nodes
    assert model.calls == math.ceil(total_nodes / graphrag_utils.GRAPHRAG_EMBED_BATCH_SIZE)
    assert max(model.batch_sizes) <= graphrag_utils.GRAPHRAG_EMBED_BATCH_SIZE


@pytest.mark.asyncio
async def test_transient_failures_are_retried_and_recovered(configure_embed_pipeline):
    model = CountingEmbedModel()
    model.fail_once_prefix = "node-16"
    logs = []
    callback = _collect_callback(logs)

    requests = [
        graphrag_utils._EmbedRequest(index=i, cache_key=f"node-{i}", text=f"node-{i}")
        for i in range(64)
    ]

    vectors = await graphrag_utils._embed_requests_with_bounded_workers(
        stage="nodes",
        embd_mdl=model,
        requests=requests,
        callback=callback,
    )

    assert len(vectors) == 64
    assert model.calls == 5  # 4 batches + 1 retry
    assert any("retry nodes batch" in msg for msg in logs)


@pytest.mark.asyncio
async def test_permanent_failure_reports_resumable_context(configure_embed_pipeline, monkeypatch):
    model = CountingEmbedModel()
    model.always_fail = True
    logs = []
    callback = _collect_callback(logs)

    class FakeDocStore:
        def delete(self, *_args, **_kwargs):
            return None

        def insert(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(graphrag_utils.settings, "docStoreConn", FakeDocStore(), raising=False)
    monkeypatch.setattr(graphrag_utils.search, "index_name", lambda _tenant_id: "idx", raising=False)

    graph = nx.Graph()
    graph.add_node("NODE_A", entity_type="PERSON", description="alpha", source_id=["doc-1"])
    graph.graph["source_id"] = ["doc-1"]
    change = graphrag_utils.GraphChange(
        added_updated_nodes={"NODE_A"},
        added_updated_edges=set(),
        removed_nodes=set(),
        removed_edges=set(),
    )

    with pytest.raises(graphrag_utils.GraphRAGEmbeddingBatchError):
        await graphrag_utils.set_graph(
            tenant_id="tenant-1",
            kb_id="kb-1",
            embd_mdl=model,
            graph=graph,
            change=change,
            callback=callback,
        )

    assert any("Task is resumable" in msg for msg in logs)


@pytest.mark.asyncio
async def test_non_transient_failure_reports_actual_attempt_count(configure_embed_pipeline):
    model = CountingEmbedModel()
    model.always_fail = True
    requests = [
        graphrag_utils._EmbedRequest(index=0, cache_key="node-0", text="node-0"),
    ]

    with pytest.raises(graphrag_utils.GraphRAGEmbeddingBatchError) as exc_info:
        await graphrag_utils._embed_requests_with_bounded_workers(
            stage="nodes",
            embd_mdl=model,
            requests=requests,
            callback=None,
        )

    assert exc_info.value.attempts == 1


@pytest.mark.asyncio
async def test_old_graph_delete_happens_after_vector_preparation(configure_embed_pipeline, monkeypatch):
    model = CountingEmbedModel()
    events = []
    logs = []
    callback = _collect_callback(logs)

    class FakeDocStore:
        def delete(self, condition, *_args, **_kwargs):
            if condition.get("knowledge_graph_kwd") == ["graph", "subgraph"]:
                events.append("delete_graph")
            else:
                events.append("delete_other")
            return None

        def insert(self, *_args, **_kwargs):
            events.append("insert")
            return None

    async def traced_thread_pool_exec(func, *args, **kwargs):
        if getattr(func, "__name__", "") == "encode":
            events.append("encode")
        return func(*args, **kwargs)

    monkeypatch.setattr(graphrag_utils, "thread_pool_exec", traced_thread_pool_exec, raising=False)
    monkeypatch.setattr(graphrag_utils.settings, "docStoreConn", FakeDocStore(), raising=False)
    monkeypatch.setattr(graphrag_utils.search, "index_name", lambda _tenant_id: "idx", raising=False)

    graph = nx.Graph()
    graph.add_node("NODE_A", entity_type="PERSON", description="alpha", source_id=["doc-1"])
    graph.add_node("NODE_B", entity_type="ORG", description="beta", source_id=["doc-1"])
    graph.add_edge(
        "NODE_A",
        "NODE_B",
        description="works_with",
        source_id=["doc-1"],
        keywords=["works_with"],
        weight=1,
    )
    graph.graph["source_id"] = ["doc-1"]

    change = graphrag_utils.GraphChange(
        added_updated_nodes={"NODE_A", "NODE_B"},
        added_updated_edges={("NODE_A", "NODE_B")},
        removed_nodes=set(),
        removed_edges=set(),
    )

    await graphrag_utils.set_graph(
        tenant_id="tenant-1",
        kb_id="kb-1",
        embd_mdl=model,
        graph=graph,
        change=change,
        callback=callback,
    )

    assert "encode" in events
    assert "delete_graph" in events
    first_delete_index = events.index("delete_graph")
    last_encode_index = max(i for i, e in enumerate(events) if e == "encode")
    assert first_delete_index > last_encode_index
