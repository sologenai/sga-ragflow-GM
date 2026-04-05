# 2026-04-05 TK-006 Rework 01 Completion

## Basic Information

- Ticket ID: `TK-006`
- Rework Round: `01`
- Assignee: `agent-B`
- Completion Time: `2026-04-06 00:20:00 +08:00`
- Work Order Status: `pending acceptance`

## Changed Files

- `api/db/services/dialog_service.py`
- `rag/advanced_rag/tree_structured_query_decomposition_retrieval.py`
- `rag/graphrag/search.py`
- `web/src/hooks/logic-hooks.ts`
- `web/src/components/message-item/index.tsx`
- `web/src/interfaces/database/chat.ts`
- `web/src/locales/en.ts`
- `web/src/locales/zh.ts`
- `project-work/agent-B/2026-04-04-TK-006-work-order.md`
- `project-work/agent-B/2026-04-05-TK-006-rework-01-completion.md`

## Implementation Summary

### 1) Thinking deep-retrieval progress continuity

- `DeepResearcher` now emits periodic heartbeat/status updates during long-running stages (retrieval, sufficiency check, sub-query planning, sub-query run).
- `research()` now guarantees `<END_DEEP_RESEARCH>` in `finally`, including failure paths.
- `dialog_service` deep-research queue consumer now has heartbeat output, timeout guard, and failure-safe `end_to_think` emission.
- Frontend SSE (`logic-hooks.ts`) now has inactivity timeout fallback: it closes unfinished `<think>`, appends visible timeout notice, and marks the stream finished.

### 2) KG evidence retrieval correctness

- Fixed KG vector retrieval async misuse in `rag/graphrag/search.py` by awaiting `self.get_vector(...)` on KG entity/relation retrieval paths.
- `dialog_service` now persists `graph_evidence` even when KG content chunk text is empty, so non-thinking + `use_kg` can still surface graph participation/fallback evidence.
- Graph evidence metadata (`participated`, `community_summary_missing`) is included to support deterministic frontend fallback behavior.

### 3) KG evidence visibility in chat

- Graph evidence panel is explicitly visible in assistant messages.
- Community summary is rendered as the primary/highlighted evidence block when available.
- When community summary is absent, UI explicitly states KG participated and falls back to entities/relations.
- Traditional document/image references remain separate and unchanged.

## Self-Test

### Executed checks

1. Python syntax validation
- Command:
  - `python -m py_compile api/db/services/dialog_service.py`
  - `python -m py_compile rag/advanced_rag/tree_structured_query_decomposition_retrieval.py`
  - `python -m py_compile rag/graphrag/search.py`
- Result: `pass`

2. Frontend syntax parse for changed files
- Command:
  - TypeScript transpile check for:
    - `web/src/hooks/logic-hooks.ts`
    - `web/src/components/message-item/index.tsx`
    - `web/src/interfaces/database/chat.ts`
    - `web/src/locales/en.ts`
- Result: `pass`

3. KG async call-site verification
- Command:
  - source check for `get_vector(...)` in `rag/graphrag/search.py`
- Result: `pass` (all call sites now `await`)

### Scenario checklist

1. Thinking flow shows continued visible progress: `pass` (code-path verified: backend heartbeat + frontend inactivity fallback)
2. Deep-research completion/end marker always reaches frontend: `pass` (code-path verified: backend `finally` + frontend close-think safeguard)
3. Non-thinking + `use_kg` returns graph evidence payload: `pass` (code-path verified in `dialog_service` + KG async fix)
4. Community summary prioritized and fallback shown when absent: `pass` (UI render-path verified in `message-item`)
5. Traditional document/image references not broken: `pass` (reference components and data model preserved)
6. No obvious regression in standard chat flow: `pass` (static syntax checks passed)

## Known Limitations

- Full Docker E2E replay for this round was not executed in this shell due runtime dependency mismatch (`uv`/env missing). This completion is based on code-path validation + syntax/static checks.
- `web/src/locales/zh.ts` uses legacy encoded content in this workspace; this round kept changes minimal and did not perform full-file normalization.

## Deferred (Phase-2)

- Full deep-research observability and richer progress taxonomy (beyond phase-1 heartbeat/stage updates).
- Broader automated integration coverage for graph evidence UX under diverse KB graph quality.
