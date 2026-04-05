# Chat Forced Knowledge Retrieval Assessment

Date: 2026-04-04
Owner: agent-x
Status: research completed

## Background

The current chat product behavior was previously adjusted toward a "force knowledge base retrieval" strategy.
Feedback indicates that answer quality and user experience became worse after this change.

## Confirmed Findings

1. Retrieval is structurally tied to the `knowledge` prompt parameter, not to query intent.
   - File: `api/db/services/dialog_service.py`
   - In `async_chat`, once a dialog has knowledge bases and `prompt_config.parameters` contains `knowledge`, the main chat path proceeds into retrieval.

2. Retrieved content is injected directly into the system prompt.
   - File: `api/db/services/dialog_service.py`
   - `kwargs["knowledge"]` is built from retrieved chunks and then formatted into `prompt_config["system"]`.

3. Dialog creation/update logic reinforces this pattern.
   - File: `api/apps/dialog_app.py`
   - If a dialog has `kb_ids` and the system prompt contains `{knowledge}`, the backend auto-adds the `knowledge` parameter.

4. Frontend defaults are also knowledge-oriented.
   - File: `web/src/pages/next-chats/hooks/use-rename-chat.ts`
   - New chat defaults still include:
     - `parameters: [{ key: "knowledge", optional: false }]`
     - `system: t("chat.systemInitialValue")`

5. Default system prompt text itself is retrieval-first.
   - File: `web/src/locales/zh.ts`
   - The default chat system prompt explicitly instructs the model to answer from the knowledge base and return a fixed "not found in the knowledge base" style answer when irrelevant.

6. The frontend already has a switch, but it is not a "disable knowledge base retrieval" switch.
   - File: `web/src/components/use-knowledge-graph-item.tsx`
   - The UI label is "Use knowledge graph".
   - File: `api/db/services/dialog_service.py`
   - Backend usage confirms `prompt_config.use_kg` only controls whether `kg_retriever` is additionally invoked.
   - It does not disable the normal knowledge base retrieval path.

7. The chat input "Thinking" button changes the retrieval workflow.
   - File: `web/src/pages/next-chats/hooks/use-send-chat-message.ts`
   - Clicking the button sends `reasoning: true` at message level.
   - File: `api/db/services/dialog_service.py`
   - When `prompt_config.reasoning` or request `reasoning` is true, the backend enters the `DeepResearcher` branch instead of the normal one-shot retrieval path.
   - File: `rag/advanced_rag/tree_structured_query_decomposition_retrieval.py`
   - `DeepResearcher` performs iterative retrieval, sufficiency checking, and multi-query decomposition.

## Why the Current Strategy Performs Poorly

1. All questions are treated as if they require retrieval.
   - Small talk, reasoning-only questions, meta-instructions, and general Q&A still pay retrieval cost.

2. Irrelevant retrieved chunks degrade answer quality.
   - Once irrelevant context is injected into the system prompt, the model is biased toward using it.

3. Prompt size and latency both increase.
   - Retrieval output is appended before generation, increasing tokens and overall response time.

4. Empty-result behavior can feel rigid.
   - If no useful chunks are found, `empty_response` may force a canned response instead of allowing a normal answer.

5. There are currently two very different "knowledge use" quality levels.
   - Normal mode: one-shot retrieval plus prompt injection.
   - Thinking mode: iterative deep research with sufficiency checks and follow-up queries.
   - This easily creates the user perception that "knowledge base only works when Thinking is enabled".

## Core Conclusion

The problem is not only "prompt wording".
The real issue is that retrieval policy is over-coupled to prompt structure and default dialog configuration.

The current design is effectively:

- if there is a knowledge base
- and the prompt uses `{knowledge}`
- then retrieve first and inject retrieval results into the system prompt

Even if the frontend "Use knowledge graph" switch is off, the normal retrieval path still runs under this design.

Likewise, the "Thinking" button is not merely a display option. It changes the retrieval strategy itself.

This is too rigid for mixed chat scenarios.

## Recommended Direction

Do not continue with "force all chat through knowledge base".

Recommended replacement:

1. Add retrieval gating before retrieval execution.
   - Only retrieve when the question is likely to require knowledge base evidence.

2. Keep a fallback strategy.
   - If direct answering is insufficient, then do retrieval as a second step.

3. Separate retrieval policy from prompt template.
   - Whether retrieval runs should not depend only on whether the system prompt contains `{knowledge}`.

4. Revisit default chat initialization.
   - New chat defaults should not automatically bias every dialog into forced retrieval mode.

## Suggested Next Step

Open a dedicated ticket for "chat retrieval gating / forced knowledge retrieval rollback optimization".
This should be treated as a product and backend behavior adjustment, not as a one-line prompt tweak.

## Related Finding: Knowledge Graph References Are Not Naturally Visible in Chat

Another related issue was confirmed during this assessment:

1. When `use_kg` is enabled, the backend inserts a synthetic knowledge-graph result into `reference.chunks`.
   - File: `api/db/services/dialog_service.py`
   - File: `rag/graphrag/search.py`

2. That KG result is not a normal document chunk.
   - It uses a pseudo title like `Related content in Knowledge Graph`
   - It has no real `doc_id`, page number, or source chunk position
   - Its content is mainly entity lists, relation lists, and community report text

3. The chat UI is still document-reference-oriented.
   - File: `web/src/components/message-item/index.tsx`
   - The document reference list is rendered from `reference.doc_aggs`
   - Since the KG result is not a normal document aggregate, it does not naturally appear in that area

4. In practice, the KG result is only visible if the final answer text explicitly cites that chunk.
   - File: `web/src/components/next-markdown-content/index.tsx`
   - The inline reference popover is driven by `[ID:x]` citations in the answer body

5. This makes the user perception misleading.
   - KG retrieval may have happened
   - but the user may still feel "no KG retrieval segment is shown"

Therefore the problem is not necessarily "KG retrieval failed".
The more likely issue is:

- KG retrieval output structure
- chat reference rendering structure

are not aligned with each other.
