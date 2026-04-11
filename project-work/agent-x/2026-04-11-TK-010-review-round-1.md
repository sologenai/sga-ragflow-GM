# 2026-04-11 TK-010 Review Round 1

## Conclusion

`TK-010` must be reopened for rework.

The previous delivery removed the import/startup blocker, but did not restore the full GraphRAG resume feature.

## Findings

### 1. Resume summary chain is still broken at runtime

The current runtime still logs:

- `Failed to get counts: 'RedisDB' object has no attribute 'hgetall'`

This means `GraphRAGTaskMonitor.get_resumable_summary()` still cannot reliably build the document-level resume summary expected by:

- `api/apps/kb_app.py`

So the compatibility surface is only partially restored.

### 2. Frontend resume/regenerate UI is not present

The frontend still contains locale keys such as:

- `resumeGraphRag`
- `regenerateGraphRag`

But the active GraphRAG generate UI path currently only exposes generic generate/pause/delete behavior and does not restore the previous dedicated resume/regenerate flow in the dataset settings experience.

Relevant files:

- `web/src/components/parse-configuration/graph-rag-form-fields.tsx`
- `web/src/pages/dataset/dataset/generate-button/generate.tsx`
- `web/src/pages/dataset/dataset/generate-button/hook.ts`

## Rework Direction

The next round must restore the feature end-to-end, not just startup:

1. Repair the Redis compatibility used by the GraphRAG resume summary path.
2. Restore the dataset-settings UI behavior so resume/regenerate becomes visible again where the project previously exposed it.

## Ticket Status

- Work order status should be treated as: `reopened for rework`
- Assignee remains: `agent-B`
