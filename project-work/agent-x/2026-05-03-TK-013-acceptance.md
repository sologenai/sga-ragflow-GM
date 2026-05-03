# 2026-05-03 TK-013 Acceptance

## Basic Information

- Ticket ID: `TK-013`
- Title: GraphRAG large-scale embedding throughput and fault-tolerance remediation
- Assignee: `agent-B`
- Acceptor: `agent-x`
- Status: `accepted`
- Accepted at: `2026-05-03`

## Acceptance Summary

`TK-013` is accepted after validation and minor acceptance rework.

The implementation addresses the remote failure pattern where GraphRAG generated a very large node set and timed out near the end of node embedding against a private embedding service.

## Accepted Scope

- GraphRAG node and edge embedding no longer creates one async task per node/edge.
- Node and edge embedding use batch calls.
- GraphRAG embedding has a dedicated concurrency limiter, separate from chat concurrency.
- Embedding batches use bounded retry with exponential backoff and jitter.
- Large embedding jobs flow through a bounded queue/worker pool.
- Progress logs report completed items and batches.
- Permanent embedding failure raises a resumable/interrupted context.
- Old graph/subgraph deletion remains after vector/chunk preparation.
- Task and GraphRAG timeouts are environment-configurable.

## Agent-X Acceptance Rework

During acceptance, agent-x found two small hardening gaps:

- `graphrag_embed_limiter` was constructed with `int(os.environ.get(...))` directly, so an invalid `GRAPHRAG_EMBED_CONCURRENCY` value could break module import before the safer parser ran.
- `GraphRAGEmbeddingBatchError.attempts` always reported the configured max retry count, even when a non-transient error stopped after one attempt.

Agent-x corrected both issues and added a unit test covering non-transient attempt reporting.

## Verification

Commands run:

```powershell
python -m py_compile rag\graphrag\utils.py rag\svr\task_executor.py test\unit_test\graphrag\test_graphrag_embed_pipeline.py
python -m pytest -q test\unit_test\graphrag\test_graphrag_embed_pipeline.py
python -m pytest test\unit_test\test_vector_mapping_compatibility.py -q
```

Results:

```text
py_compile passed
5 passed in 2.13s
9 passed in 0.12s
```

## Residual Risks

- Validation used mocked embedding workloads, not a real remote 32k-node replay.
- If index insertion fails after old graph deletion, recovery still depends on existing resume/regenerate paths.
- Provider-specific transient error messages may still require future marker additions if a private service emits unusual error formats.

## Decision

Accepted.
