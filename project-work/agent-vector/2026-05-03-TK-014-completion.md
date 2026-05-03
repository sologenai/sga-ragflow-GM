# 2026-05-03 TK-014 Completion Audit

## Status

- Ticket: `TK-014`
- Assignee: `agent-vector`
- Status: `pending acceptance`
- Completed at: `2026-05-03`

## Changed Files

- `conf/mapping.json`
- `conf/os_mapping.json`
- `common/doc_store/vector_mapping.py`
- `common/doc_store/es_conn_base.py`
- `rag/utils/opensearch_conn.py`
- `rag/svr/task_executor.py`
- `test/unit_test/test_vector_mapping_compatibility.py`
- `project-work/agent-vector/2026-05-03-TK-014-work-order.md`

Agent-x acceptance rework also updated:

- `common/doc_store/vector_mapping.py`
- `common/doc_store/es_conn_base.py`
- `rag/utils/opensearch_conn.py`
- `test/unit_test/test_vector_mapping_compatibility.py`

## Supported Dimensions

OpenSearch mappings now cover:

```text
128
256
384
512
768
1024
1536
2048
2560
3072
4096
6144
8192
10240
```

Elasticsearch mappings cover the backend-supported subset:

```text
128
256
384
512
768
1024
1536
2048
2560
3072
4096
```

## Implementation Notes

- Elasticsearch uses `dense_vector` dynamic templates with `dims` matching `q_<dim>_vec` through 4096 dimensions, which is the Elasticsearch `dense_vector` limit for this deployment family.
- OpenSearch uses `knn_vector` dynamic templates with `dimension` matching `q_<dim>_vec`.
- Runtime vector dimensions are also supported beyond the mainstream template list where the backend permits them. For Elasticsearch, any positive returned dimension up to 4096 can be repaired as a concrete `q_<dim>_vec` mapping; only dimensions above 4096 are blocked with an actionable backend-limit error.
- Existing Elasticsearch/OpenSearch indexes are repaired non-destructively from `create_idx()` when the index already exists.
- The repair path adds missing concrete vector fields through `indices.put_mapping`; it does not delete indexes, delete documents, or reindex data.
- The repair path is idempotent: if all required vector fields already exist, no mapping update is sent.
- `init_kb()` now raises an actionable error containing model name, returned dimension, document engine, index name, missing mapping field, and recommended action when index creation or repair fails.
- OceanBase already creates vector columns dynamically in `common/doc_store/ob_conn_base.py`.
- Infinity already creates the requested `q_<dim>_vec` column dynamically in `common/doc_store/infinity_conn_base.py`.

## Existing-Index Repair Instructions

Remote rollout procedure:

1. Deploy the updated code and restart backend/task executor processes.
2. Re-run or resume a parse task for the affected knowledge base.
3. During `init_kb()`, RAGFlow checks the tenant index and adds missing vector fields for the mainstream dimension set.
4. Confirm logs contain an entry like:

```text
ESConnection repaired vector fields for index ragflow_<tenant_id>: already present q_1024_vec; added q_4096_vec
```

or:

```text
OSConnection repaired vector fields for index ragflow_<tenant_id>: already present q_1024_vec; added q_3072_vec
```

If `put_mapping` fails because the engine version does not support a requested vector dimension, the safest fallback is to configure an embedding output dimension supported by that backend, then reparse affected documents. Elasticsearch rejects 6144, 8192, and 10240 dimensional `dense_vector` fields; use OpenSearch, Infinity, or OceanBase for those dimensions, or configure the embedding model to return 4096 dimensions or fewer. Do not delete existing indexes or knowledge bases as part of this remediation.

## Tests

Commands run:

```powershell
python -m json.tool conf\mapping.json > $null
python -m json.tool conf\os_mapping.json > $null
python -m pytest test\unit_test\test_vector_mapping_compatibility.py -q
```

Results:

```text
mapping.json valid
os_mapping.json valid
9 passed in 0.10s
```

The pytest coverage includes:

- Elasticsearch required-dimension presence check.
- OpenSearch required-dimension presence check.
- Existing-index repair idempotency check.
- Simulated `q_4096_vec` compatibility repair check.
- Elasticsearch runtime dimension support for a non-mainstream but backend-supported dimension.
- Elasticsearch runtime rejection for dimensions above the backend limit.

## Residual Risks

- Elasticsearch does not support 6144, 8192, or 10240 dimensional `dense_vector` fields; this patch reports that as an actionable backend limit instead of creating invalid mappings.
- Existing documents parsed with an older embedding dimension remain under their old `q_<dim>_vec` field. Changing models still requires reparsing documents for semantically correct retrieval with the new embedding space.
- `rag/svr/task_executor.py` had pre-existing uncommitted changes from another work stream; this remediation only added vector mapping validation/error handling around `init_kb()`.
