# Upstream RAGFlow Chat Retrieval Review

Date: 2026-04-04
Owner: agent-x
Status: completed
Upstream repository: https://github.com/infiniflow/ragflow
Branch checked: `main`

## Summary

Current upstream RAGFlow main branch does not appear to have solved the chat retrieval problem in a fundamentally different way.

The upstream design is still centered around:

- a default retrieval-first chat prompt
- a default `knowledge` variable in chat prompt parameters
- normal retrieval when `knowledge` is present
- a separate `reasoning` mode that upgrades retrieval into a deeper iterative workflow
- a separate `use_kg` switch that only controls additional knowledge-graph retrieval

## Confirmed Upstream Findings

1. Upstream still ships a retrieval-first default chat prompt.
   - File: `api/apps/restful_apis/chat_api.py`
   - `_DEFAULT_PROMPT_CONFIG["system"]` still contains a knowledge-base-only answer template and `{knowledge}` placeholder.

2. Upstream still injects `knowledge` as a default required parameter.
   - File: `api/apps/restful_apis/chat_api.py`
   - `_DEFAULT_PROMPT_CONFIG["parameters"] = [{"key": "knowledge", "optional": False}]`

3. Upstream still auto-fills the `knowledge` parameter when a chat has datasets and the prompt contains `{knowledge}`.
   - File: `api/apps/restful_apis/chat_api.py`
   - `_apply_prompt_defaults()` keeps this pattern.

4. Upstream new chat defaults still follow the same structure.
   - File: `web/src/pages/next-chats/hooks/use-rename-chat.ts`
   - Default values still include:
     - `system: t("chat.systemInitialValue")`
     - `use_kg: false`
     - `reasoning: false`
     - `parameters: [{ key: "knowledge", optional: false }]`

5. Upstream normal retrieval still depends on whether the prompt parameters contain `knowledge`.
   - File: `api/db/services/dialog_service.py`
   - Retrieval branch starts when `"knowledge" in param_keys`.

6. Upstream `use_kg` is not a master retrieval switch.
   - File: `api/db/services/dialog_service.py`
   - `use_kg` only decides whether to additionally invoke `kg_retriever`.

7. Upstream "Thinking" behavior is still tied to `reasoning`.
   - File: `web/src/pages/next-chats/hooks/use-send-chat-message.ts`
   - Clicking the input-level Thinking button sends `reasoning: enableThinking`.
   - File: `api/db/services/dialog_service.py`
   - When `reasoning` is true, backend switches to `DeepResearcher`.

8. Upstream `DeepResearcher` is materially different from normal retrieval.
   - File: `rag/advanced_rag/tree_structured_query_decomposition_retrieval.py`
   - It performs iterative retrieval, sufficiency checking, and follow-up query decomposition.

## Practical Conclusion

Upstream native RAGFlow has not really separated these three things:

- whether a chat should use dataset retrieval
- whether a chat should use knowledge graph retrieval
- whether a message should enter deep reasoning / deep research mode

As a result:

- `use_kg` means "use knowledge graph retrieval enhancement"
- `reasoning` means "upgrade to deep research workflow"
- but normal knowledge-base retrieval still remains the default as long as the prompt structure is knowledge-oriented

This matches the local behavior we observed.

## Decision Impact

If we want better mixed chat quality, we should not expect upstream native behavior to solve it automatically.

We will likely need a local product adjustment that explicitly separates:

1. retrieval policy
2. deep research policy
3. knowledge graph enhancement policy

Recommended future direction:

- retrieval mode: `auto / always / off`
- deep research mode: `auto / manual`
- knowledge graph mode: `on / off`

This is cleaner than relying on current upstream defaults.
