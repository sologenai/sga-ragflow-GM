# 2026-05-05 GraphRAG Timeout Watchdog Fix

## Background

Remote UI showed GraphRAG still failing with:

```text
Get embedding of nodes: 5758/31441, batches 284/1890
[ERROR][Exception]: GraphRAG execution timed out after 21600s. Task is resumable.
```

The progress lines prove the batching implementation is active. The failure was caused by the hard `GRAPHRAG_TASK_TIMEOUT_SECONDS=21600` wrapper around the entire GraphRAG job. For large knowledge bases, entity extraction, graph merge, and post-processing can consume most of the six-hour window before node embedding starts. The task was killed even though embedding was still making visible progress.

## Change

Updated `rag/svr/task_executor.py`:

- `GRAPHRAG_TASK_TIMEOUT_SECONDS` now defaults to `0`, meaning no hard total-time timeout by default.
- Added `GRAPHRAG_NO_PROGRESS_TIMEOUT_SECONDS`, default `10800` seconds.
- Added `_await_graphrag_with_timeouts()` to monitor GraphRAG progress.
- Wrapped the GraphRAG progress callback so every progress message refreshes the no-progress watchdog.
- If `GRAPHRAG_TASK_TIMEOUT_SECONDS > 0`, it remains available as an explicit hard total-time limit.
- If GraphRAG makes no progress for `GRAPHRAG_NO_PROGRESS_TIMEOUT_SECONDS`, it is interrupted with a resumable error.

## Operator Guidance

For the remote case in the screenshot, use the new default behavior or explicitly set:

```text
GRAPHRAG_TASK_TIMEOUT_SECONDS=0
GRAPHRAG_NO_PROGRESS_TIMEOUT_SECONDS=10800
GRAPHRAG_EMBED_BATCH_SIZE=16
GRAPHRAG_EMBED_CONCURRENCY=2
```

If the private embedding service is stable and the task keeps producing batch progress, let it continue. If there is no progress for 3 hours, investigate the embedding or LLM service before resuming.

## Validation

Commands run:

```powershell
python -m py_compile rag\svr\task_executor.py
python -m pytest -q test\unit_test\graphrag\test_graphrag_embed_pipeline.py test\unit_test\test_vector_mapping_compatibility.py
```

Results:

```text
py_compile passed
14 passed in 4.98s
```

## Residual Risk

This change removes the default hard wall-clock limit for GraphRAG. Protection now comes from cancellation, task state, and the no-progress watchdog. Operators can still set `GRAPHRAG_TASK_TIMEOUT_SECONDS` if they need a hard upper bound.
