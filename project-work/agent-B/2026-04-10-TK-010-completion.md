# 2026-04-10 TK-010 Completion

## Basic Information

- Ticket ID: `TK-010`
- Assignee: `agent-B`
- Completion Time: `2026-04-11 02:58:00 +08:00`
- Work Order Status: `pending acceptance`

## Changed Files

- `rag/utils/redis_conn.py`
- `rag/graphrag/task_monitor.py`
- `web/src/pages/dataset/dataset/generate-button/hook.ts`
- `web/src/pages/dataset/dataset/generate-button/generate.tsx` (updated again on `2026-04-11` for running-phase graph stats visibility)
- `web/src/components/parse-configuration/graph-rag-form-fields.tsx`
- `web/src/locales/zh.ts`
- `project-work/agent-B/2026-04-10-TK-010-work-order.md`
- `project-work/agent-B/2026-04-10-TK-010-completion.md`

## Implementation Summary

### 1) Resume summary runtime chain fixed

- Added missing Redis wrapper APIs required by current GraphRAG task monitor path:
  - `setex`, `keys`, `pipeline`, `expire`, `hset`, `hget`, `hgetall`, `hincrby`
- Added Redis bytes/string decoding in task monitor summary methods:
  - `get_doc_progress_all`
  - `get_counts`
  - `get_resume_from_task_id`
- Result: `/v1/kb/trace_graphrag` no longer raises `RedisDB has no attribute hgetall`-type runtime errors.

### 2) Dataset settings Resume/Regenerate entry restored

- Extended GraphRAG generate hook to support explicit mode:
  - `generate | resume | regenerate`
- `runGraphRag` request payload now carries `resume` explicitly for GraphRAG mode.
- Restored visible actions in GraphRAG UI:
  - Settings page GraphRAG card now shows `Resume / Regenerate`.
  - Dataset generate dropdown GraphRAG item also shows `Resume / Regenerate`.
- Reused and surfaced existing locale keys:
  - `resumeGraphRag`, `regenerateGraphRag`, `docProgressSummary`, `graphAlreadyGenerated`, `graphRegenerateHint`

### 3) Container + browser validation + image rebuild

- Synced patched source files into running `docker-ragflow-gpu-1`.
- Rebuilt frontend assets in container and restarted service.
- Used browser automation to:
  - Login
  - Open dataset settings
  - Verify `Resume / Regenerate` buttons visible
  - Click both buttons and observe backend API path returns 200
- Built deployment image from repository source:
  - `docker build -t ragflow:tk010-rework-01 -f Dockerfile .`
- Recreated `ragflow-gpu` service from the new image and confirmed startup readiness in logs.
- Re-verified **after image recreate** by browser automation:
  - `POST /v1/kb/run_graphrag` (Resume) => `200`
  - `POST /v1/kb/run_graphrag` (Regenerate) => `200`
  - `GET /v1/kb/trace_graphrag` => `200`
- Exported offline image artifact for remote transfer:
  - `docker/artifacts/ragflow-tk010-rework-01.tar` (`~3.58GB`)

## Self-Test

1. resume summary runtime path: `pass`  
   - `/v1/kb/trace_graphrag` returns `doc_summary` and no `hgetall` runtime exception.
2. Redis hash compatibility for task monitor: `pass`  
   - Container script self-test on `GraphRAGTaskMonitor` hash/pipeline/counter path passed.
3. dataset settings resume entry visible: `pass`  
   - Settings page GraphRAG card showed `Resume` button.
4. regenerate entry visible: `pass`  
   - Settings page GraphRAG card showed `Regenerate` button.
5. non-GraphRAG startup path not regressed: `pass`  
   - New image container starts and serves `/v1/system/version` (authorized request returned 200).
6. GPU image startup no longer fails on task_monitor mismatch: `pass`  
   - `ragflow-gpu` recreated from new image and reached server ready state.
7. post-restart browser click verification (resume/regenerate): `pass`  
   - New-image container UI path verified and API calls returned `200`.

## Known Limitations

- Current environment still logs `Realtime synonym is disabled, since no redis connection.` from existing environment/config state; not introduced by this ticket.
- `doc_summary.has_progress` can still be `false` when no doc-level progress hash is persisted by upstream execution path; this round fixed runtime compatibility and API/UI chain continuity.

## 2026-04-11 Audit Supplement (UI Runtime Visibility Closure)

### Background

- During user validation, a gap was identified:
  - GraphRAG generation dropdown showed progress percentage and logs
  - but did not always show `node/edge/entity/relation/community` counts during the **running** phase
- This caused confusion that graph statistics were unavailable until completion.

### Root Cause

- In `generate.tsx`, graph stats and doc summary rendering were gated by completion/failure-oriented conditions.
- Specifically:
  - stats display depended on `showGraphResumeActions`-like completed/failed state
  - running state often had no visible stats line in the active menu item

### Code Changes (Detailed)

- File: `web/src/pages/dataset/dataset/generate-button/generate.tsx`
- Key adjustments:
  1. `buildGraphStatsSummary(...)` now supports `options.showWhenEmpty`
     - normalizes missing `graph_summary` fields to `0`
     - can intentionally render zero-value stats during running phase
  2. Added runtime display gates:
     - `showGraphStatsSummary = isGraphType && status !== start`
     - `showDocProgressSummary = isGraphType && status !== start && doc_summary.has_progress`
  3. Running-phase behavior:
     - when `status === running`, stats line is rendered with `showWhenEmpty: true`
     - user sees `Graph stats: nodes 0 / edges 0 / entities 0 / relations 0 / communities 0` first, then values update by polling
  4. Completed/failed behavior:
     - existing Resume/Regenerate entry and progress summary logic are preserved

### Compatibility / Non-Regression Scope

- No backend API contract change in this supplemental closure.
- No GraphRAG retrieval/execution logic change.
- No removal of existing UI capabilities:
  - Resume/Regenerate buttons preserved
  - trace polling behavior preserved
  - existing document/image reference flows unaffected

### Validation Trail

1. Static check:
   - `eslint` passed for `generate.tsx` target path.
2. Frontend build:
   - `npm run build` passed in `web/`.
3. Runtime deployment:
   - built frontend assets copied into `docker-ragflow-gpu-1:/ragflow/web/dist`
   - container restarted successfully.
4. Browser verification (Playwright CLI):
   - logged into dataset page
   - opened `Generate` dropdown while GraphRAG task in progress
   - observed visible runtime stats line:
     - `Graph stats: nodes 0 / edges 0 / entities 0 / relations 0 / communities 0`
   - observed running percentage (e.g., `60.00%`) and streaming progress log simultaneously.

### Evidence Artifacts

- Screenshot (runtime UI proof):
  - `output/playwright/tk010-running-stats.png`
- Playwright runtime snapshot containing the visible stats line:
  - `.playwright-cli/page-2026-04-11T02-54-05-319Z.yml`

### Supplemental Self-Test Matrix

1. Graph stats visible during running phase: `pass`
2. Running phase still shows percent/progress log: `pass`
3. Resume/Regenerate actions still visible for completed/failed graph tasks: `pass`
4. Existing GraphRAG API path unaffected by this UI-only patch: `pass`

