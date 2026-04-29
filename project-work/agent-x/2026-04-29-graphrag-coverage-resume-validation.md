# 2026-04-29 GraphRAG coverage display and resume validation

## Scope

- Project branch: `GM202604`
- Runtime image verified locally: `ragflow-custom:latest`
- Local container verified: `docker-ragflow-gpu-1`
- Test knowledge base: `test`
- Test URL: `http://localhost:8880/dataset/dataset/6b23ee1e30c311f1b9e4f584472b9517`

## Display issue

The generation menu used to show the latest task progress as if it were the whole graph status.
For a no-op incremental run, this caused a misleading line like `merged 0/1, skipped 1` even though the graph already existed.

The UI now separates two meanings:

- Completed graph state shows graph coverage from `graph_summary`: in-graph document count, total document count, and pending document count.
- Running or interrupted task state shows task progress from `doc_summary`: completed, merged, failed, skipped.
- Graph statistics remain a separate line: nodes, edges, entities, relations, communities.

## Files changed

- `web/src/pages/dataset/dataset/generate-button/generate.tsx`
- `web/src/locales/zh.ts`
- `web/src/locales/en.ts`

## Local page verification

After rebuilding and recreating the local runtime container, the `test` knowledge base menu shows:

- `Graph coverage`: 1 document in graph out of 1, 0 pending incremental documents.
- `Graph stats`: 21 nodes, 16 edges, 0 entities, 0 relations, 0 communities.
- `Incremental update`: disabled because no new documents are pending.
- `Regenerate`: available, but protected by the regenerate confirmation flow.

This confirms the display no longer mixes a historical skipped task with current graph coverage.

## Resume-chain code verification

The interrupted resume path is implemented as document-level resume, not full regeneration:

- `api/apps/kb_app.py` accepts GraphRAG modes: `incremental`, `resume_failed`, and `regenerate`.
- `cancel_graphrag` marks the current GraphRAG task as `progress=-1` and writes the Redis cancel flag.
- `resume_failed` requires an existing failed/interrupted task and writes `graphrag:resume:{new_task_id}` to point to the old task.
- `rag/graphrag/general/index.py` reads the resume pointer, collects previously `merged` docs, also reads existing graph `source_id`, and skips those documents during the resumed run.
- Timeout and provider/model failures are recorded per document as failed docs; the task remains resumable instead of being treated as a clean success.

## Remaining manual validation

A full UI interruption test has not been executed on the existing `test` knowledge base because triggering it through the UI requires `Regenerate`, which deletes the current graph before rebuilding.

Recommended next validation:

- Use a throwaway knowledge base, or confirm that the existing `test` knowledge base may be regenerated.
- Start GraphRAG generation.
- Cancel while a document is processing.
- Confirm the task becomes interrupted and the menu shows `Resume interrupted run`.
- Click resume and confirm logs show existing merged docs being skipped and only unfinished docs being processed.

## Commit

- Code commit: `98dd735a2 fix: clarify GraphRAG coverage summary`
