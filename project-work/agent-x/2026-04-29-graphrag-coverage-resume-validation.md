# 2026-04-29 GraphRAG coverage display and resume validation

## Scope

- Project branch: `GM202604`
- Runtime image verified locally: `ragflow-custom:latest` / `ragflow:GM202604-20260429-graph-stats`
- Local container verified: `docker-ragflow-gpu-1`
- Test knowledge base: `test`
- Test URL: `http://localhost:8880/dataset/dataset/6b23ee1e30c311f1b9e4f584472b9517`

## Display issue

The generation menu used to show the latest task progress as if it were the whole graph status.
For a no-op incremental run, this caused a misleading line like `merged 0/1, skipped 1` even though the graph already existed.

The UI now separates these meanings:

- Completed graph state shows graph coverage from `graph_summary`: in-graph document count, total document count, and pending document count.
- Running or interrupted task state shows task progress from `doc_summary`: completed, merged, failed, skipped.
- Graph statistics now uses the active graph JSON as the authoritative source for entity/node and relation/edge totals.
- The UI label is normalized to `entities/nodes`, `relations/edges`, and `communities` to avoid implying separate active totals.

## Files changed

- `web/src/pages/dataset/dataset/generate-button/generate.tsx`
- `api/apps/kb_app.py`
- `web/src/locales/zh.ts`
- `web/src/locales/en.ts`

## Local page verification

After rebuilding and recreating the local runtime container, the `test` knowledge base settings page shows:

- `Graph coverage`: 2 documents in graph out of 2, 0 pending incremental documents.
- `Graph stats`: 268 entities/nodes, 230 relations/edges, 24 communities.
- `Incremental update`: disabled because no new documents are pending.
- `Regenerate`: available, but protected by the regenerate confirmation flow.

This confirms the display no longer mixes a historical skipped task with current graph coverage.

The first browser refresh after the container rebuild still showed the old graph stats text because the browser reused the previous entry bundle. Reopening the same settings URL with `?v=graph-stats-20260429` loaded the new `web/dist` entry and confirmed the final UI string:

- `图谱统计：实体/节点 268，关系/边 230，社区 24`
- `图谱覆盖：已入图 2/2，待增量 0`

## Resume-chain code verification

The interrupted resume path is implemented as document-level resume, not full regeneration:

- `api/apps/kb_app.py` accepts GraphRAG modes: `incremental`, `resume_failed`, and `regenerate`.
- `cancel_graphrag` marks the current GraphRAG task as `progress=-1` and writes the Redis cancel flag.
- `resume_failed` requires an existing failed/interrupted task and writes `graphrag:resume:{new_task_id}` to point to the old task.
- `rag/graphrag/general/index.py` reads the resume pointer, collects previously `merged` docs, also reads existing graph `source_id`, and skips those documents during the resumed run.
- Timeout and provider/model failures are recorded per document as failed docs; the task remains resumable instead of being treated as a clean success.

## Real UI interruption and resume validation

The real UI interruption flow was executed on the existing `test` knowledge base after explicit approval.

Validation steps:

- Opened the `test` knowledge base in the local browser.
- Started GraphRAG from the UI.
- Manually interrupted the task during execution.
- Confirmed the task became interrupted and the UI showed the `中断续跑` action.
- Clicked `中断续跑` from the UI.
- Confirmed the backend created a new GraphRAG task with `resume_failed` semantics.

Observed task chain:

- `40f4484e43da11f1ab14ddc2ae9b7945`: manually interrupted during extraction before global merge; DB progress became `-1`.
- `94cdf24443da11f1ab14ddc2ae9b7945`: resumed from `40f4484e43da11f1ab14ddc2ae9b7945`; log showed `skip 0 merged docs, process 2 docs` because the first interruption happened before any document reached durable global merge.
- `94cdf24443da11f1ab14ddc2ae9b7945`: completed both document merges and graph resolution, then was manually interrupted during community generation.
- `4aa601a643db11f1ab14ddc2ae9b7945`: resumed from `94cdf24443da11f1ab14ddc2ae9b7945`; log showed `skip 2 merged docs, process 0 docs`, proving merged documents are skipped on resume.
- `4aa601a643db11f1ab14ddc2ae9b7945`: completed community generation and finished with DB progress `1`.

Final verified UI state:

- `图谱统计：实体/节点 268，关系/边 230，社区 24`
- `图谱覆盖：已入图 2/2，待增量 0`
- `增量更新` is disabled because there are no pending documents.
- `重新生成` remains available for explicit full rebuild.

Validation conclusion:

- Human interruption before merge is resumable, but it must reprocess documents that did not reach durable global merge.
- Human interruption after merge is true checkpoint resume: the next run skips merged documents and continues downstream work.
- The same path also applies to model timeout, quota exhaustion, or provider failure when those failures leave the GraphRAG task at `progress=-1`.

## Commit

- Code commit: `98dd735a2 fix: clarify GraphRAG coverage summary`
- Follow-up commit pending: normalize GraphRAG active stats and UI labels.
