# 2026-04-29 TK-012 Acceptance

## Basic Information

- Ticket ID: `TK-012`
- Reviewer: `agent-x`
- Result: `accepted`
- Review Date: `2026-04-29`

## Acceptance Summary

The GraphRAG resume feature is now materially different from the previous UI-only/compatibility restoration:

- document progress is written by the actual GraphRAG execution path
- merged documents become durable checkpoints
- timeout/quota/model-provider failures keep the task resumable
- resume skips documents already merged or already present in the graph
- post-processing can resume after all documents have been merged
- SDK and UI paths now share the same resume semantics
- GraphRAG now has three explicit product modes:
  - `resume_failed`: interrupted-task checkpoint resume
  - `incremental`: new-file-only update
  - `regenerate`: delete and rebuild
- The UI only enables incremental update when trace detects new files and requires confirmation before regenerate deletes the graph.
- Manual cancellation preserves the previous GraphRAG task id and graph data so `resume_failed` can continue from the interrupted task.

## Source Review

Reviewed changes in:

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

The implementation matches the requested scenario:

1. If document A/B are merged and document C fails from timeout/quota, the task is marked failed.
2. Clicking `Resume interrupted run` creates a new GraphRAG task with a resume pointer.
3. The new task skips A/B by Redis monitor state and docStore graph `source_id`.
4. The new task retries C and then continues post-processing.

## Verification

Commands run:

```powershell
python -m compileall rag\graphrag\general\index.py rag\graphrag\utils.py rag\svr\task_executor.py api\apps\sdk\dataset.py
npm.cmd exec -- eslint src/pages/dataset/dataset/generate-button/generate.tsx src/pages/dataset/dataset/generate-button/hook.ts --max-warnings 0
npm.cmd run build
git diff --check
docker compose up -d --force-recreate ragflow-gpu
Invoke-WebRequest -UseBasicParsing -Uri http://localhost:8880 -TimeoutSec 30
```

Result:

- Compile check passed.
- Targeted frontend ESLint passed.
- Frontend production build passed.
- Diff whitespace check passed, with only expected CRLF warnings from the Windows working copy.
- Docker image `ragflow-custom:latest` points to `sha256:a08d50b9e584266d0b2734391825e812a87539d0fbf5e286572d3609fc247c52` and the recreated local container served HTTP `200` on port `8880`.

## Acceptance Notes

This closes the functional gap identified after TK-010. A real provider-side timeout/quota end-to-end test still requires a running environment with controllable model limits, but the code-level resume chain is now connected end to end.
