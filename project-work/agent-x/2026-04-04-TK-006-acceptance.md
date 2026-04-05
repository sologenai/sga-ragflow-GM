# TK-006 Acceptance

- Ticket ID: `TK-006`
- Reviewed By: `agent-x`
- Acceptance Time: `2026-04-05 00:06:00 +08:00`
- Result: `accepted`

## Reviewed Scope

Accepted phase-1 scope includes:

1. retrieval strategy decoupling for chat
2. preservation of `Thinking` as the explicit stronger path
3. preservation of `use_kg` as graph enhancement
4. explicit graph evidence propagation and presentation
5. minimal settings-page expansion via lightweight retrieval mode

## Reviewed Files

- `api/db/services/dialog_service.py`
- `api/apps/dialog_app.py`
- `api/apps/sdk/session.py`
- `api/apps/chunk_app.py`
- `rag/nlp/search.py`
- `rag/graphrag/search.py`
- `web/src/pages/next-chats/hooks/use-send-chat-message.ts`
- `web/src/pages/next-chats/hooks/use-send-multiple-message.ts`
- `web/src/pages/next-chats/hooks/use-send-shared-message.ts`
- `web/src/pages/next-chats/hooks/use-rename-chat.ts`
- `web/src/pages/next-chats/chat/app-settings/chat-prompt-engine.tsx`
- `web/src/pages/next-chats/chat/app-settings/use-chat-setting-schema.tsx`
- `web/src/components/message-item/index.tsx`
- `web/src/components/next-markdown-content/index.tsx`
- `web/src/interfaces/database/chat.ts`
- `web/src/locales/zh.ts`
- `web/src/locales/en.ts`
- `project-work/agent-B/2026-04-04-TK-006-completion.md`

## Acceptance Notes

1. Backend now supports `prompt_config.retrieval_mode` with controlled values `auto/always/off`.
2. Normal chat no longer blindly depends on forced retrieval whenever a knowledge base is bound.
3. `Thinking` remains available and still acts as the explicit stronger retrieval path through per-message override.
4. Mixed retrieval remains in place, while lexical/vector fusion is no longer hard-coded to a single fixed pair of weights.
5. Knowledge-graph results are now propagated as structured `graph_evidence` and are no longer dependent only on pseudo-chunk behavior to become visible.
6. Frontend changes stayed within first-phase scope and did not replace the existing developer-facing settings model.

## Verification Performed

1. Manual code review of retrieval, routing, and graph-evidence chains: **PASS**
2. Python compile check for six backend files:
   - `api/db/services/dialog_service.py`
   - `api/apps/dialog_app.py`
   - `api/apps/sdk/session.py`
   - `api/apps/chunk_app.py`
   - `rag/nlp/search.py`
   - `rag/graphrag/search.py`
   Result: **PASS**

## Residual Limits

1. Full frontend lint verification was not completed because the current environment is missing `eslint-plugin-react-refresh`.
2. Full repository TypeScript verification remains limited by pre-existing workspace baseline errors unrelated to this ticket.
3. Browser-side end-to-end interaction verification was not completed in the current environment.
4. Phase-1 still uses lightweight heuristic routing for `auto`; it is not yet a learned or feedback-driven retrieval router.

## Final Judgment

`TK-006` is accepted as a controlled infrastructure phase-1 delivery. The change stays within agreed scope, preserves existing controls, improves default retrieval behavior, and makes graph evidence visible without forcing a large chat-settings redesign.
