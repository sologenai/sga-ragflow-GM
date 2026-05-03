# 2026-05-03 TK-013 Completion

## Basic Information

- Ticket ID: `TK-013`
- Assignee: `agent-B`
- Completion Time: `2026-05-03 23:55:00 +08:00`
- Work Order Status: `accepted`

## Changed Files

- `rag/graphrag/utils.py`
- `rag/svr/task_executor.py`
- `test/unit_test/graphrag/test_graphrag_embed_pipeline.py` (new)
- `project-work/agent-B/2026-05-03-TK-013-work-order.md`
- `project-work/agent-B/2026-05-03-TK-013-completion.md` (new)

Agent-x acceptance rework also updated:

- `rag/graphrag/utils.py`
- `test/unit_test/graphrag/test_graphrag_embed_pipeline.py`

## Implementation Summary

### 1) GraphRAG embedding batching + deterministic mapping

Implemented in `rag/graphrag/utils.py`:

- Added ordered request model `_EmbedRequest(index, cache_key, text)`.
- Reworked `set_graph(...)` node/edge embedding flow from per-item task fan-out to batched pipeline.
- Node and edge input order is deterministic (`sorted(...)`), and output vectors are mapped back by index.
- Added env-configurable batch size:
  - `GRAPHRAG_EMBED_BATCH_SIZE` (default `16`)

### 2) Dedicated GraphRAG embedding limiter

Implemented in `rag/graphrag/utils.py`:

- Added dedicated semaphore:
  - `graphrag_embed_limiter = asyncio.Semaphore(GRAPHRAG_EMBED_CONCURRENCY)`
- Added env-configurable concurrency:
  - `GRAPHRAG_EMBED_CONCURRENCY` (default `2`)
- This is independent from `MAX_CONCURRENT_CHATS`.

### 3) Bounded queue / worker pool backpressure

Implemented in `rag/graphrag/utils.py`:

- Added `_embed_requests_with_bounded_workers(...)`:
  - bounded `asyncio.Queue` (size from env)
  - fixed worker count (`min(concurrency, total_batches)`)
  - producer + worker model
  - no longer one async task per node/edge
- Added queue size env:
  - `GRAPHRAG_EMBED_QUEUE_SIZE` (default `max(4, GRAPHRAG_EMBED_CONCURRENCY * 4)`)
- Added batch/item progress callbacks:
  - `Get embedding of nodes: X/Y, batches A/B`
  - `Get embedding of edges: X/Y, batches A/B`

### 4) Retry / backoff / jitter + failure context

Implemented in `rag/graphrag/utils.py`:

- Added `_encode_batch_with_retry(...)` with:
  - bounded retry attempts
  - exponential backoff + jitter
  - transient error classification (`timeout`, connection reset/abort/refused, 429, 5xx, etc.)
  - structured logs: stage, batch index, attempt, batch size, elapsed, reason
- Added env-configurable retry controls:
  - `GRAPHRAG_EMBED_MAX_RETRIES` (default `3`)
  - `GRAPHRAG_EMBED_RETRY_BASE_SECONDS` (default `2`)
  - `GRAPHRAG_EMBED_RETRY_MAX_SECONDS` (default `60`)
- Added explicit permanent failure exception:
  - `GraphRAGEmbeddingBatchError`
- On permanent failure, callback now emits resumable guidance:
  - `Task is resumable; please use Resume after tuning batch/concurrency/timeout.`

### 5) Configurable task timeout (global + GraphRAG)

Implemented in `rag/svr/task_executor.py`:

- Added env parsing helper `_env_int(...)`.
- Added env-controlled timeout vars:
  - `RAGFLOW_TASK_TIMEOUT_SECONDS` (default `10800`)
  - `GRAPHRAG_TASK_TIMEOUT_SECONDS` (default `21600`)
- Replaced hardcoded `@timeout(60*60*3,1)` with `@timeout(DO_HANDLE_TASK_TIMEOUT_SECONDS,1)`.
- Wrapped GraphRAG execution with `asyncio.wait_for(..., timeout=GRAPHRAG_TASK_TIMEOUT_SECONDS)` and timeout hint message.

### 6) Large-graph fault-tolerance behavior

Implemented in `rag/graphrag/utils.py`:

- Old graph (`graph/subgraph`) deletion remains after vector/chunk preparation stage, not before embedding stage.
- If embedding batch fails permanently, run aborts with resumable context and does not proceed silently.

## Agent-X Acceptance Rework

During acceptance, agent-x made two small hardening changes:

- `GRAPHRAG_EMBED_CONCURRENCY` now uses the safe parsed value when constructing `graphrag_embed_limiter`, instead of calling `int(os.environ[...])` directly during module import.
- `GraphRAGEmbeddingBatchError.attempts` now reports the actual attempt count. Non-transient failures that stop after the first attempt no longer report the configured max retry count.

The acceptance rework added one extra unit test for non-transient failure attempt reporting.

## New Environment Variables

- `GRAPHRAG_EMBED_BATCH_SIZE` (default `16`)
- `GRAPHRAG_EMBED_CONCURRENCY` (default `2`)
- `GRAPHRAG_EMBED_QUEUE_SIZE` (default `max(4, concurrency*4)`)
- `GRAPHRAG_EMBED_MAX_RETRIES` (default `3`)
- `GRAPHRAG_EMBED_RETRY_BASE_SECONDS` (default `2`)
- `GRAPHRAG_EMBED_RETRY_MAX_SECONDS` (default `60`)
- `RAGFLOW_TASK_TIMEOUT_SECONDS` (default `10800`)
- `GRAPHRAG_TASK_TIMEOUT_SECONDS` (default `21600`)

## Self-Test and Evidence

### Command 1

```bash
python -m py_compile rag/graphrag/utils.py rag/svr/task_executor.py test/unit_test/graphrag/test_graphrag_embed_pipeline.py
```

Result: `pass`

### Command 2

```bash
python -m pytest -q test/unit_test/graphrag/test_graphrag_embed_pipeline.py
```

Result after agent-x acceptance rework: `5 passed`

Covered assertions:

1. `Mocked 32000 nodes batching reduces request count`: `pass`
   - verifies `encode` request count equals `ceil(total / batch_size)`
2. `Transient failure retry and recover`: `pass`
   - injected timeout once; recovered on retry; retry callback observed
3. `Permanent failure marks run resumable/interrupted context`: `pass`
   - raises `GraphRAGEmbeddingBatchError`; callback contains resumable message
4. `Old graph deletion after vector preparation`: `pass`
   - event order asserts `delete_graph` happens after `encode`
5. `Non-transient failure reports actual attempt count`: `pass`
   - permanent non-transient failure stops after one attempt and reports `attempts == 1`

## Recommended Remote Settings (private embedding endpoint, ~32k nodes)

### Conservative (CPU / single worker)

```text
GRAPHRAG_EMBED_BATCH_SIZE=8
GRAPHRAG_EMBED_CONCURRENCY=1
GRAPHRAG_EMBED_MAX_RETRIES=4
GRAPHRAG_EMBED_RETRY_BASE_SECONDS=3
GRAPHRAG_EMBED_RETRY_MAX_SECONDS=90
GRAPHRAG_TASK_TIMEOUT_SECONDS=28800
RAGFLOW_TASK_TIMEOUT_SECONDS=14400
THREAD_POOL_MAX_WORKERS=32
MAX_CONCURRENT_CHATS=2
```

### Balanced (single GPU, stable private endpoint)

```text
GRAPHRAG_EMBED_BATCH_SIZE=16
GRAPHRAG_EMBED_CONCURRENCY=2
GRAPHRAG_EMBED_MAX_RETRIES=3
GRAPHRAG_EMBED_RETRY_BASE_SECONDS=2
GRAPHRAG_EMBED_RETRY_MAX_SECONDS=60
GRAPHRAG_TASK_TIMEOUT_SECONDS=21600
RAGFLOW_TASK_TIMEOUT_SECONDS=10800
THREAD_POOL_MAX_WORKERS=64
MAX_CONCURRENT_CHATS=3
```

### Aggressive (multi-worker GPU endpoint)

```text
GRAPHRAG_EMBED_BATCH_SIZE=24
GRAPHRAG_EMBED_CONCURRENCY=3
GRAPHRAG_EMBED_MAX_RETRIES=3
GRAPHRAG_EMBED_RETRY_BASE_SECONDS=2
GRAPHRAG_EMBED_RETRY_MAX_SECONDS=45
GRAPHRAG_TASK_TIMEOUT_SECONDS=21600
RAGFLOW_TASK_TIMEOUT_SECONDS=10800
THREAD_POOL_MAX_WORKERS=96
MAX_CONCURRENT_CHATS=4
```

Tuning rule:

- Raise `BATCH_SIZE` first when endpoint supports true batched embedding.
- Raise `CONCURRENCY` only after observing no queue timeout / 429 / 5xx spikes.
- Keep GraphRAG jobs serialized when endpoint saturation appears in logs.

## Residual Risks

- This round validates with mocked embedding workload, not a full remote 32k real endpoint replay.
- If index insertion fails after old graph deletion, recovery still depends on existing resume/regenerate paths.
- Transient error classification is message-based for part of providers; custom provider error formats may need additional markers.

## Handoff Notes to Agent-X

- Core remediation scope for TK-013 is implemented in source, not hot patch.
- Batch + bounded queue + dedicated limiter + retry/backoff + timeout parameterization are all landed.
- Ticket status updated to `pending acceptance`.
