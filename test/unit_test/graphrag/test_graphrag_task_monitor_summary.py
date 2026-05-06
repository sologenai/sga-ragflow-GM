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

import json
import sys
import types

if "rag.utils.redis_conn" not in sys.modules:
    sys.modules["rag.utils.redis_conn"] = types.SimpleNamespace(REDIS_CONN=None)

from rag.graphrag.task_monitor import GraphRAGTaskMonitor


class _FakeRedis:
    def __init__(self):
        self.hashes = {}
        self.values = {}

    def pipeline(self):
        return self

    def hset(self, key, field=None, value=None, mapping=None):
        bucket = self.hashes.setdefault(key, {})
        if mapping is not None:
            bucket.update(mapping)
        elif field is not None:
            bucket[field] = value
        return self

    def hget(self, key, field):
        return self.hashes.get(key, {}).get(field)

    def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    def hincrby(self, key, field, amount):
        bucket = self.hashes.setdefault(key, {})
        bucket[field] = int(bucket.get(field, 0)) + amount
        return self

    def expire(self, *_args, **_kwargs):
        return self

    def setex(self, key, _ttl, value):
        self.values[key] = value
        return self

    def get(self, key):
        return self.values.get(key)

    def execute(self):
        return []


def test_extracted_doc_progress_is_visible_before_global_merge():
    monitor = GraphRAGTaskMonitor(redis_conn=_FakeRedis())
    task_id = "task-progress"
    docs = [
        {"doc_id": "doc-1", "doc_name": "one.pdf", "chunk_count": 3},
        {"doc_id": "doc-2", "doc_name": "two.pdf", "chunk_count": 5},
    ]

    assert monitor.init_doc_progress(task_id, docs)
    monitor.update_doc_status(task_id, "doc-1", "extracting", start_time=1.0)

    summary = monitor.get_resumable_summary(task_id)
    assert summary["started"] == 1
    assert summary["completed"] == 0
    assert summary["extracting"] == 1
    assert summary["pending"] == 1

    monitor.update_doc_status(
        task_id,
        "doc-1",
        "extracted",
        entity_count=7,
        relation_count=4,
        end_time=2.0,
    )

    summary = monitor.get_resumable_summary(task_id)
    assert summary["started"] == 1
    assert summary["completed"] == 1
    assert summary["extracted"] == 1
    assert summary["merged"] == 0
    assert summary["entity_count"] == 7
    assert summary["relation_count"] == 4

    monitor.update_doc_status(task_id, "doc-1", "merged", end_time=3.0)

    summary = monitor.get_resumable_summary(task_id)
    assert summary["started"] == 1
    assert summary["completed"] == 1
    assert summary["extracted"] == 0
    assert summary["merged"] == 1
    assert summary["entity_count"] == 7
    assert summary["relation_count"] == 4


def test_summary_derives_extracted_counts_for_legacy_tasks_without_counter_hash():
    redis_conn = _FakeRedis()
    monitor = GraphRAGTaskMonitor(redis_conn=redis_conn)
    task_id = "legacy-task"
    redis_conn.hset(
        monitor._doc_hash_key(task_id),
        "doc-1",
        json.dumps(
            {
                "doc_id": "doc-1",
                "doc_name": "one.pdf",
                "status": "generated",
                "entity_count": 3,
                "relation_count": 2,
                "chunk_count": 1,
                "start_time": 1.0,
                "end_time": 2.0,
                "error": "",
            }
        ),
    )

    summary = monitor.get_resumable_summary(task_id)
    assert summary["has_progress"] is True
    assert summary["total_docs"] == 1
    assert summary["started"] == 1
    assert summary["completed"] == 1
    assert summary["extracted"] == 1
    assert summary["entity_count"] == 3
    assert summary["relation_count"] == 2
