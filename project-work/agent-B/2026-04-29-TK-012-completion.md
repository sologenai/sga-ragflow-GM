# 2026-04-29 TK-012 Completion

## Basic Information

- Ticket ID: `TK-012`
- Owner: `agent-B`
- Completed By: `agent-x`
- Status: `accepted`
- Completion Time: `2026-04-29`

## Changed Files

- `api/apps/kb_app.py`
- `api/apps/sdk/dataset.py`
- `api/db/services/document_service.py`
- `rag/graphrag/general/index.py`
- `rag/graphrag/utils.py`
- `rag/svr/task_executor.py`
- `web/src/pages/dataset/dataset/generate-button/generate.tsx`
- `web/src/pages/dataset/dataset/generate-button/hook.ts`
- `web/src/locales/en.ts`
- `web/src/locales/zh.ts`
- `project-work/2026-04-04-ticket-board.md`
- `project-work/agent-B/2026-04-29-TK-012-work-order.md`
- `project-work/agent-B/2026-04-29-TK-012-completion.md`
- `project-work/agent-x/2026-04-29-TK-012-acceptance.md`

## Implementation Summary

### 1. Execution path now records real document checkpoints

`run_graphrag_for_kb()` now initializes `GraphRAGTaskMonitor` for every GraphRAG task and writes document state during execution:

- `pending` when the task starts
- `extracting` when a document starts subgraph generation
- `merged` after a document graph is durably merged into the global graph
- `failed` when timeout/model/quota/provider errors affect a document
- `skipped` when a document is already represented in the graph or has no chunks

### 2. Resume skips durable work

Resume now reads:

- previous merged/skipped document ids from Redis task monitor
- current graph `source_id` from docStore

The new task skips those documents and only processes unfinished documents. This protects against cases where Redis progress is missing but the graph was already durably written.

### 3. Partial failures remain resumable

If any document fails, the task executor now marks the GraphRAG task as failed (`progress = -1`) instead of reporting successful completion. This keeps the UI/API resume path available and avoids hiding quota/timeout failures.

### 4. Post-processing resume is supported

If all documents are already merged and the previous failed task has a resume pointer, resume can continue into resolution/community post-processing using the existing global graph.

When document-level failures exist, post-processing is intentionally paused. The next resume should first complete the missing documents, then run post-processing on a complete graph.

### 5. SDK path aligned

The token SDK endpoint `/datasets/<dataset_id>/run_graphrag` now accepts explicit `mode` values and still supports legacy `resume: true`. SDK trace now includes `doc_summary`.

Supported modes:

- `resume_failed`: continue after manual cancellation, model timeout, quota exhaustion, or provider failure.
- `incremental`: process newly added files while preserving the existing graph.
- `regenerate`: delete the existing graph and rebuild from scratch.

### 6. Safer graph replacement

`set_graph()` now builds all graph/subgraph/entity/relation chunks before deleting the old graph/subgraph records. This reduces the risk that quota/timeout/vector failures erase a previously resumable graph.

### 7. Manual cancellation preserves resume state

The GraphRAG pause action now calls `/kb/cancel_graphrag` directly. It no longer calls `unbind_task`, so it does not clear `kb.graphrag_task_id` and does not delete the current graph. This keeps manual cancellation resumable.

### 8. Safer UI actions

The GraphRAG UI now separates the three product actions:

- `中断续跑`: shown for interrupted/failed graph tasks.
- `增量更新`: shown for completed graph tasks and enabled only when trace detects new files not represented in the graph.
- `重新生成`: always goes through a confirmation modal warning that the current graph will be deleted.

## Verification

- `python -m compileall rag\graphrag\general\index.py rag\graphrag\utils.py rag\svr\task_executor.py api\apps\sdk\dataset.py` passed.
- `npm.cmd exec -- eslint src/pages/dataset/dataset/generate-button/generate.tsx src/pages/dataset/dataset/generate-button/hook.ts --max-warnings 0` passed.
- `git diff --check` passed with only existing Windows CRLF warnings.
- `npm.cmd run build` passed for `web`.
- Docker image built and tagged:
  - `ragflow:GM202604-20260429-graphrag-modes`
  - `ragflow:GM202604`
  - `ragflow-custom:latest`
- Local container `docker-ragflow-gpu-1` was recreated from `ragflow-custom:latest`.
- `http://localhost:8880` returned HTTP `200`.

## Residual Risk

Full graph replacement is still not a true docStore transaction. The patch moves model/vector failure risk before deletion, which closes the main timeout/quota failure class, but an infrastructure failure during the final docStore delete/insert window can still require manual recovery from backups or regeneration.
