# Graph Community Summary UI Plan

- Date: `2026-04-05`
- Author: `agent-x`
- Related Ticket: `TK-008`

## Product Judgment

The current graph-evidence feature is already useful and should not be reduced.

The real issue is not correctness, but visual weight:

- the community summary often occupies too much vertical space
- users need to see that graph evidence participated
- users also need quick access to entities and relations

## Recommended UI Direction

The preferred first refinement is:

1. keep community summary in the evidence card
2. collapse it by default
3. provide a clear expand / collapse action
4. preserve full text when expanded
5. keep entity / relation sections easy to scan without forcing summary expansion

## Why This Direction

- It preserves information value.
- It improves readability in long-chat contexts.
- It avoids a modal-heavy interaction.
- It stays within a very small frontend-only scope.

## Non-Goals

- no retrieval changes
- no graph backend changes
- no large layout redesign
- no removal of community summary
