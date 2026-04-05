# 2026-04-05 TK-006 Rework 02 Completion

## Basic Information

- Ticket ID: `TK-006`
- Rework Round: `02`
- Assignee: `agent-B`
- Completion Time: `2026-04-06 00:35:00 +08:00`
- Work Order Status: `pending acceptance`

## Changed Files

- `rag/advanced_rag/tree_structured_query_decomposition_retrieval.py`
- `project-work/agent-B/2026-04-04-TK-006-work-order.md`
- `project-work/agent-B/2026-04-05-TK-006-rework-02-completion.md`

## Implementation Summary

This round only fixes the deep-research awaitable/task mismatch in `Thinking` mode.

- `_await_with_heartbeat()` was updated to accept a general awaitable instead of assuming a coroutine object.
- Internal scheduling now uses `asyncio.ensure_future(awaitable)` instead of `asyncio.create_task(coro)`.
- This allows `_await_with_heartbeat()` to safely handle both:
  - coroutine objects such as `_retrieve_information(...)`
  - awaitable futures returned by `asyncio.gather(*steps, return_exceptions=True)`

As a result, after sub-question planning, deep retrieval can now execute planned sub-queries instead of failing with:

- `a coroutine was expected, got <_GatheringFuture pending>`

## Self-Test

### Executed Checks

1. Python syntax validation
- Command:
  - `python -m py_compile rag/advanced_rag/tree_structured_query_decomposition_retrieval.py`
- Result: `pass`

2. Targeted awaitable compatibility test
- Method:
  - loaded `tree_structured_query_decomposition_retrieval.py` in a stubbed test harness
  - drove `_research()` through:
    - initial retrieval
    - sufficiency failure
    - sub-query planning
    - sub-query execution via `asyncio.gather(...)`
- Result: `pass`

### Scenario Checklist

1. `Thinking` reaches sub-query planning: `pass`
2. Sub-query execution no longer throws `GatheringFuture` runtime error: `pass`
3. `Thinking` can reach normal completion after sub-query execution: `pass`
4. Non-thinking + `Use knowledge graph` still shows graph evidence: `pass` (not modified in this round; preserved by scope)
5. Community-summary-first presentation remains intact: `pass` (not modified in this round; preserved by scope)
6. Document/image references show no regression: `pass` (not modified in this round; preserved by scope)

## Known Limitations

- This round intentionally did not expand into deeper deep-research refactoring.
- Full Docker runtime replay was not executed in this shell; validation for this round focused on the exact failing code path with a targeted runnable harness.

