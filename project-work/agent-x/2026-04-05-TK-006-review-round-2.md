# TK-006 Review Round 2

- Ticket ID: `TK-006`
- Reviewed By: `agent-x`
- Review Time: `2026-04-05 18:05:00 +08:00`
- Result: `rework required`
- Validation Image: `ragflow-custom:tk006-tk007-r1`

## Review Trigger

Rebuilt-image runtime verification was performed after `agent-B` completed the first rework round.

The rebuilt image was tested against real local models and a real graph-enabled dialog in Docker.

## Verified Improvements

### 1. `Thinking` no longer looks frozen after the first retrieval lines

Runtime behavior is improved compared with the previous failure mode.

Observed improvements:

- visible progress now continues beyond `Searching by ...`
- the stream no longer appears dead after the first retrieval result
- the frontend receives a clear end to the stream instead of hanging indefinitely

### 2. Non-thinking + knowledge graph now produces visible graph evidence

Observed in rebuilt-image runtime verification:

- non-thinking chat with graph-enabled dialog returned final `graph_evidence`
- graph evidence contained:
  - `communities: 1`
  - `relations: 6`
- graph participation is now user-visible in the chat response

### 3. Community-summary-first graph presentation is working

When community-summary evidence exists, it is now surfaced as the strongest graph-evidence path.

This is aligned with the revised phase-1 intent.

## Blocking Finding

### Deep retrieval still fails when executing planned sub-queries

The rebuilt image still shows a runtime failure during the deeper part of `Thinking` mode.

Observed runtime progression:

1. retrieval starts
2. sufficiency check runs
3. the system plans next-step sub-queries
4. deep retrieval then fails with:

`a coroutine was expected, got <_GatheringFuture pending>`

User-visible result:

- the UI no longer appears frozen
- but the stronger deep-retrieval path still degrades into an internal-failure fallback instead of actually completing the planned sub-query execution

Relevant file:

- `rag/advanced_rag/tree_structured_query_decomposition_retrieval.py`

Likely root cause:

- `_await_with_heartbeat()` currently wraps its input with `asyncio.create_task(coro)`
- later the code passes `asyncio.gather(*steps, return_exceptions=True)` into `_await_with_heartbeat()`
- `asyncio.gather(...)` returns an awaitable future, not a coroutine object
- `create_task()` therefore raises the runtime error seen in Docker validation

## Review Judgment

`TK-006` remains reopened for rework.

The first rework round successfully solved:

1. perceived frozen progress
2. graph-evidence visibility for non-thinking graph-enabled chat

But the stronger `Thinking` path still has a blocking functional failure in the deep-research sub-query stage, so the ticket cannot be accepted yet.
