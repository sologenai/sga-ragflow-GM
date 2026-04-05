# TK-006 Review Round 1

- Ticket ID: `TK-006`
- Reviewed By: `agent-x`
- Review Time: `2026-04-05 16:20:00 +08:00`
- Result: `rework required`

## Review Trigger

Live verification on the local Docker deployment revealed that the previously accepted phase-1 delivery does not yet meet user-facing expectations in two critical runtime paths:

1. when `Thinking` is enabled, the chat UI can remain visually stuck after the initial retrieval lines
2. when `Thinking` is disabled but `Use knowledge graph` is enabled, users still cannot reliably see graph evidence in the chat experience

## Findings

### 1. Deep-research progress appears stuck after the initial retrieval step

The `Thinking` path still routes into `DeepResearcher` and emits the first retrieval messages, but the current user experience makes the session look frozen once the UI stops receiving visible stage updates.

Relevant files:

- `api/db/services/dialog_service.py`
- `rag/advanced_rag/tree_structured_query_decomposition_retrieval.py`
- `web/src/hooks/logic-hooks.ts`

Observed behavior:

- frontend displays lines such as `Searching by ...` and `Retrieval ...`
- subsequent deep-research steps are not made visible clearly enough to reassure the user that the task is still running
- any missing terminal progress or missing completion marker causes the user to perceive the session as stuck

### 2. Knowledge-graph evidence retrieval has a runtime bug

Local container logs show runtime warnings:

- `coroutine 'Dealer.get_vector' was never awaited`

This points to the current knowledge-graph retrieval code path using async vector retrieval incorrectly.

Relevant file:

- `rag/graphrag/search.py`

Impact:

- graph entity / relation retrieval can become empty unexpectedly
- `graph_evidence` may not be populated with meaningful data
- frontend graph-evidence panel therefore has nothing useful to show even though `Use knowledge graph` is enabled

### 3. Graph evidence visibility is still too conditional

Live verification confirms that graph evidence can already appear in the dedicated graph-evidence panel, especially when the knowledge-graph build has produced usable community-summary output. The remaining issue is that this visibility is still too conditional and easy for users to miss.

Relevant files:

- `web/src/components/message-item/index.tsx`
- `web/src/components/next-markdown-content/index.tsx`

Impact:

- users often look at the traditional citation/reference area first and conclude that knowledge-graph retrieval did not run
- graph participation becomes much easier to perceive when a community summary exists, but much weaker when only entities/relations are available
- when community-summary evidence is absent, the UI still needs a stronger fallback presentation or an explicit notice that graph retrieval ran but no displayable community summary was produced

## Review Judgment

`TK-006` must be reopened for rework.

The original phase-1 direction remains valid, but runtime verification shows the delivery is not yet good enough in:

1. deep-research progress visibility
2. graph-evidence retrieval correctness
3. graph-evidence user-facing discoverability
