# 2026-05-03 TK-014 Acceptance

## Basic Information

- Ticket ID: `TK-014`
- Title: Mainstream embedding vector-dimension compatibility remediation
- Assignee: `agent-vector`
- Acceptor: `agent-x`
- Status: `accepted`
- Accepted at: `2026-05-03`

## Acceptance Summary

`TK-014` is accepted after validation and one small acceptance rework.

The delivered remediation covers the remote `qwen3-vl-embedding` failure mode where embedding configuration succeeds but parsing or retrieval fails because the document-engine vector mapping does not support the returned dimension.

## Accepted Scope

- Elasticsearch mapping now includes mainstream dimensions up to the backend-supported 4096 limit.
- OpenSearch mapping now includes the requested mainstream dimension set through 10240.
- Existing ES/OpenSearch indexes can be repaired non-destructively through idempotent `put_mapping` updates.
- New and existing indexes can receive concrete `q_<dim>_vec` fields for the current runtime embedding dimension.
- ES runtime dimensions under or equal to 4096 are accepted even if they are not in the mainstream template list.
- ES dimensions above 4096 are rejected with an actionable backend-limit message.
- Early task failure now includes model name, returned dimension, document engine, index name, missing mapping, and recommended action.

## Agent-X Acceptance Rework

During acceptance, agent-x found that Elasticsearch originally accepted only the fixed mainstream list. That would still require a code change for a future supported dimension such as `2000`.

Agent-x corrected this by adding runtime dimension handling:

- `vector_dims_for_index("elasticsearch", vector_size)` returns the mainstream list plus the actual returned dimension when `vector_size <= 4096`.
- `vector_dims_for_index("elasticsearch", 6144)` raises a clear backend-limit error.
- OpenSearch now uses the same helper and remains able to add the current runtime dimension.
- Tests now cover both the non-mainstream supported ES dimension case and the ES backend-limit rejection case.

## Verification

Commands run:

```powershell
python -m json.tool conf\mapping.json > $null
python -m json.tool conf\os_mapping.json > $null
python -m pytest test\unit_test\test_vector_mapping_compatibility.py -q
python -m py_compile common\doc_store\vector_mapping.py common\doc_store\es_conn_base.py rag\utils\opensearch_conn.py rag\svr\task_executor.py
```

Results:

```text
mapping ok
os_mapping ok
9 passed in 0.10s
py_compile passed
```

## Residual Risks

- Elasticsearch still cannot store 6144, 8192, or 10240 dimensional dense vectors. This is treated as a backend limitation, not a RAGFlow mapping gap.
- Existing documents parsed with a previous embedding model remain in the old vector space and must be reparsed for semantically correct retrieval after model changes.
- `rag/svr/task_executor.py`, `rag/graphrag/utils.py`, `project-work/agent-B/2026-05-03-TK-013-work-order.md`, and `test/unit_test/graphrag/` contain parallel `TK-013` worktree changes. They were not accepted as part of `TK-014`.

## Decision

Accepted.
