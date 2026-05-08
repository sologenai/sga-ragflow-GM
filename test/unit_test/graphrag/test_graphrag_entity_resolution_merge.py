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

import asyncio
import hashlib
import sys
import types

import networkx as nx
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

    sys.modules["xxhash"] = types.SimpleNamespace(xxh64=lambda data=b"": _FakeXXHash(data))

if "api.db.services.task_service" not in sys.modules:
    api_mod = types.ModuleType("api")
    api_mod.__path__ = []
    db_mod = types.ModuleType("api.db")
    db_mod.__path__ = []
    services_mod = types.ModuleType("api.db.services")
    services_mod.__path__ = []
    task_service_mod = types.ModuleType("api.db.services.task_service")
    task_service_mod.has_canceled = lambda *_args, **_kwargs: False
    sys.modules.setdefault("api", api_mod)
    sys.modules.setdefault("api.db", db_mod)
    sys.modules.setdefault("api.db.services", services_mod)
    sys.modules["api.db.services.task_service"] = task_service_mod

if "rag.nlp" not in sys.modules:
    fake_rag_tokenizer = types.SimpleNamespace(
        tokenize=lambda txt: txt.split() if isinstance(txt, str) else [],
        fine_grained_tokenize=lambda txt: txt.split() if isinstance(txt, str) else [],
    )
    fake_search = types.SimpleNamespace(index_name=lambda _tenant_id: "idx")
    fake_nlp = types.SimpleNamespace(
        is_english=lambda value: isinstance(value, str) and value.isascii(),
        rag_tokenizer=fake_rag_tokenizer,
        search=fake_search,
    )
    sys.modules["rag.nlp"] = fake_nlp
    sys.modules["rag.nlp.rag_tokenizer"] = fake_rag_tokenizer
    sys.modules["rag.nlp.search"] = fake_search

if "rag.llm.chat_model" not in sys.modules:
    sys.modules["rag.llm.chat_model"] = types.SimpleNamespace(Base=object)

if "rag.prompts.generator" not in sys.modules:
    sys.modules["rag.prompts.generator"] = types.SimpleNamespace(
        message_fit_in=lambda messages, _max_length: (0, messages)
    )

if "common.settings" not in sys.modules:
    fake_doc_store_conn = types.SimpleNamespace(delete=lambda *args, **kwargs: None, insert=lambda *args, **kwargs: None)
    fake_retriever = types.SimpleNamespace(search=lambda *args, **kwargs: None)
    fake_settings = types.SimpleNamespace(docStoreConn=fake_doc_store_conn, retriever=fake_retriever)
    sys.modules["common.settings"] = fake_settings

if "rag.utils.redis_conn" not in sys.modules:
    class _FakeRedisConn:
        def get(self, *_args, **_kwargs):
            return None

        def set(self, *_args, **_kwargs):
            return None

    sys.modules["rag.utils.redis_conn"] = types.SimpleNamespace(REDIS_CONN=_FakeRedisConn())

if "editdistance" not in sys.modules:
    sys.modules["editdistance"] = types.SimpleNamespace(eval=lambda left, right: abs(len(left) - len(right)))

from rag.graphrag.entity_resolution import EntityResolution
from rag.graphrag.general.extractor import Extractor
from rag.graphrag.utils import GraphChange


class _FakeLLM:
    llm_name = "fake-llm"
    max_length = 4096


def _add_node(graph, name, entity_type="TYPE"):
    graph.add_node(
        name,
        entity_name=name,
        entity_type=entity_type,
        description=name,
        source_id=[name],
    )


def _add_edge(graph, source, target):
    graph.add_edge(
        source,
        target,
        src_id=source,
        tgt_id=target,
        description=f"{source}-{target}",
        keywords=[source, target],
        weight=1,
        source_id=[source, target],
    )


@pytest.mark.asyncio
async def test_merge_graph_nodes_uses_neighbor_snapshot(monkeypatch):
    extractor = Extractor(_FakeLLM())
    async def no_summary(_self, _name, description, task_id=""):
        return description

    monkeypatch.setattr(Extractor, "_handle_entity_relation_summary", no_summary, raising=False)

    graph = nx.Graph()
    for node in ("DUP_A", "DUP_B", "DUP_C", "KEEP_1", "KEEP_2"):
        _add_node(graph, node)
    _add_edge(graph, "DUP_A", "KEEP_1")
    _add_edge(graph, "DUP_B", "KEEP_1")
    _add_edge(graph, "DUP_B", "KEEP_2")
    _add_edge(graph, "DUP_C", "KEEP_2")

    change = GraphChange()
    await extractor._merge_graph_nodes(graph, ["DUP_A", "DUP_B", "DUP_C"], change)

    assert graph.has_node("DUP_A")
    assert not graph.has_node("DUP_B")
    assert not graph.has_node("DUP_C")
    assert graph.has_edge("DUP_A", "KEEP_1")
    assert graph.has_edge("DUP_A", "KEEP_2")
    assert {"DUP_B", "DUP_C"}.issubset(change.removed_nodes)


@pytest.mark.asyncio
async def test_entity_resolution_serializes_graph_mutation(monkeypatch):
    resolver = EntityResolution(_FakeLLM())
    active_merges = 0
    max_active_merges = 0

    def is_similarity(_self, left, right):
        return left.split("_")[0] == right.split("_")[0]

    async def resolve_all(_self, candidate_resolution_i, resolution_result, resolution_result_lock, task_id=""):
        async with resolution_result_lock:
            resolution_result.update(candidate_resolution_i[1])

    async def traced_merge(_self, _graph, _nodes, _change, _task_id=""):
        nonlocal active_merges, max_active_merges
        active_merges += 1
        max_active_merges = max(max_active_merges, active_merges)
        await asyncio.sleep(0.01)
        active_merges -= 1

    monkeypatch.setattr(EntityResolution, "is_similarity", is_similarity, raising=False)
    monkeypatch.setattr(EntityResolution, "_resolve_candidate", resolve_all, raising=False)
    monkeypatch.setattr(EntityResolution, "_merge_graph_nodes", traced_merge, raising=False)

    graph = nx.Graph()
    for node in ("A_1", "A_2", "B_1", "B_2"):
        _add_node(graph, node)

    await resolver(graph, set(graph.nodes()), callback=lambda **_kwargs: None)

    assert max_active_merges == 1
