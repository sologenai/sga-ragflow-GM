# TK-006 Acceptance Round 2

- Ticket ID: `TK-006`
- Reviewed By: `agent-x`
- Acceptance Time: `2026-04-05 18:25:00 +08:00`
- Validation Image: `ragflow-custom:tk006-tk007-r2`
- Result: `accepted`

## Acceptance Conclusion

This ticket is accepted after second-round rebuilt-image runtime verification.

The previously blocking `Thinking` failure during sub-query execution is no longer present.

## Runtime Verification Performed

Verification was executed against the rebuilt local Docker image `ragflow-custom:tk006-tk007-r2` with the real configured model path and the real graph-enabled dialog already present in the local environment.

### 1. Non-thinking + graph-enabled chat

Observed outcome:

- chat completed normally
- final response returned structured `graph_evidence`
- returned graph evidence contained:
  - `communities: 1`
  - `relations: 6`
- community-summary-first graph presentation remained intact

Conclusion:

- non-thinking + `Use knowledge graph` remains functional
- graph participation is visible to the user

### 2. `Thinking` runtime path

Observed outcome:

- `Thinking` kept streaming visible progress
- progress advanced through:
  - initial retrieval
  - sufficiency checking
  - next-step planning
  - deeper execution path
- stream completed normally with a final event
- no `GatheringFuture` crash appeared in the user-visible stream
- no `Deep retrieval failed: a coroutine was expected, got <_GatheringFuture pending>` log pattern appeared in the container logs

Additional runtime indicators:

- final stream completed successfully
- event count was substantially larger than the previously broken run
- the user-visible progress no longer stopped at the initial retrieval stage

## Verified Fix

Reviewed file:

- `rag/advanced_rag/tree_structured_query_decomposition_retrieval.py`

Confirmed effect:

- `_await_with_heartbeat()` now handles general awaitables safely
- the deep-research flow no longer breaks when wrapping `asyncio.gather(...)`
- planned sub-query execution no longer falls into the previous runtime failure mode

## Residual Notes

- In the verified query, the tail of the deep-research path reached the max-depth boundary for several generated sub-queries and then returned the collected answer. This is acceptable for the current phase-1 scope and is not a crash.
- Current environment validation was performed with API-level runtime execution against the rebuilt container, not a browser automation harness.
- The startup path still depends on the persistent `.venv` volume state and may spend time checking/installing runtime dependencies such as `torch` on first boot in a fresh environment.

## Final Judgment

`TK-006` is accepted.
