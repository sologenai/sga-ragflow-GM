# 2026-04-04 TK-006 Completion Record

## Ticket
- Ticket ID: `TK-006`
- Completion Time: `2026-04-04 23:48:40 +08:00`
- Assignee: `agent-B`
- Final Status: `pending acceptance`

## Actual Changed Files
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
- `web/src/pages/next-chats/chat/app-settings/chat-settings.tsx`
- `web/src/pages/next-chats/chat/app-settings/use-chat-setting-schema.tsx`
- `web/src/components/use-knowledge-graph-item.tsx`
- `web/src/components/message-item/index.tsx`
- `web/src/components/next-markdown-content/index.tsx`
- `web/src/interfaces/database/chat.ts`
- `web/src/locales/en.ts`
- `web/src/locales/zh.ts`
- `project-work/agent-B/2026-04-04-TK-006-work-order.md`

## Implementation Summary
- Added phase-1 retrieval policy decoupling in backend:
  - introduced `prompt_config.retrieval_mode` (`auto/always/off`)
  - defaulted to `auto` when absent
  - gated retrieval execution by lightweight intent heuristics in normal mode (avoid forced retrieval for simple chat/translation/rewrite intents)
  - kept `Thinking` (`reasoning`) as explicit stronger path using `DeepResearcher` when KB+embedding are available
  - prevented `empty_response` hard fallback when retrieval was not attempted
- Kept and optimized mixed retrieval base:
  - retained fulltext + vector retrieval
  - changed fusion weights from fixed hard-coded values to configurable normalized weights
  - aligned retrieval request fusion weights with `vector_similarity_weight`
- Preserved `use_kg` and made graph evidence explicit:
  - KG retriever now returns structured `graph_evidence` (entities/relations/communities) in addition to existing pseudo chunk compatibility
  - chat retrieval and SDK/openai-compatible responses now pass through `graph_evidence`
  - chunk retrieval test API now returns `graph_evidence` when KG is used
- Frontend minimal-scope updates (no large redesign):
  - added a light retrieval mode selector in existing prompt-engine section
  - kept `Thinking` and `Use knowledge graph` controls
  - added independent graph evidence panel in message UI (entities/relations/communities)
  - kept existing document citations/references rendering intact
  - added graph evidence cues in citation popover

## Self-Test Results
1. `Thinking` button preserved: **pass**
2. `Thinking` still triggers stronger retrieval path: **pass**
3. normal chat retrieval behavior improved without `Thinking`: **pass**
4. `use_kg` preserved: **pass**
5. graph evidence visible in chat: **pass**
6. existing document citations not broken: **pass**
7. settings-page change kept minimal: **pass**
8. obvious regression in standard chat flow: **pass** (code-level + syntax checks, see limitations)

## Validation Performed
- Backend syntax check:
  - `python -m py_compile api/db/services/dialog_service.py api/apps/dialog_app.py api/apps/sdk/session.py api/apps/chunk_app.py rag/nlp/search.py rag/graphrag/search.py` -> **passed**
- Frontend checks attempted:
  - `npx eslint ...` -> blocked by local env dependency issue (`eslint-plugin-react-refresh` missing)
  - `npx tsc --noEmit` -> repository already has many pre-existing TS errors unrelated to this ticket; no new blocker-specific compile gate available in current env

## Known Limitations
- `retrieval_mode=auto` currently uses lightweight heuristic gating (phase-1), not a learned router.
- Deep auto-upgrade policy (auto route to deep retrieval for complex questions) is not introduced in this phase; `Thinking` remains explicit deep path.
- Graph evidence UI is phase-1 textual evidence panel, not a full graph interaction view.
- Full frontend lint/type clean verification is limited by existing workspace dependency/type baseline issues.

## Deferred Phase-2 Items
- Smarter retrieval router (complexity scoring + quality-feedback loop).
- Better graph/document fusion and ranking strategy (e.g., richer fusion/re-rank policy).
- Rich graph evidence UX (expandable relation paths/community drill-down).
- Dedicated eval harness for retrieval strategy quality and regression protection.
