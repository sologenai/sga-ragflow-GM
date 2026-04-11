# 2026-04-04 Ticket Board

## Active Tickets

| Ticket | Title | Owner | Status | Priority | Note |
| --- | --- | --- | --- | --- | --- |
| TK-001 | Knowledgebase list auto-classification by naming rule | `agent-a` | `accepted` | `medium-high` | First-phase delivery accepted; current implementation uses local fetch-and-paginate after loading up to 1000 records |
| TK-002 | Model management supports deleting a single model | `agent-001` | `accepted` | `medium` | Frontend delete entry completed and accepted; browser-side click validation and full lint verification were not completed in current environment |
| TK-003 | Knowledgebase fixed labels, manual labeling, and list filtering | `agent-a` | `accepted` | `medium` | Fixed-label persistence, manual labeling, list filtering, and locale-backed menu text are now accepted; local pagination limitation remains |
| TK-004 | Admin/User password change failure remediation | `agent-002` | `accepted` | `high` | Root-cause fix accepted in admin server password-update chain; historical affected accounts still require one more reset or guided remediation after deployment |
| TK-005 | System prompt leakage remediation | `agent-003` | `accepted` | `high` | Agent path, ordinary chat path, and prompt-field stripping are now accepted; current environment still lacks full pytest/end-to-end verification |
| TK-006 | Chat retrieval phase-1 optimization and graph evidence presentation | `agent-B` | `accepted` | `high` | Rebuilt-image runtime verification now passes: `Thinking` no longer freezes, deep retrieval completes without the `GatheringFuture` crash, and non-thinking graph-enabled chat returns visible graph evidence |
| TK-007 | Password flow correction and admin unlock capability | `agent-02` | `accepted` | `high` | Rebuilt-image runtime verification passed for admin reset, ordinary-user self-service password change, lock message, lock state, and admin unlock |
| TK-008 | Graph community summary collapsible display optimization | `agent-B` | `accepted` | `medium` | Frontend-only follow-up accepted: both community summary and entity/relation evidence are now compact by default with explicit expand/collapse controls |
| TK-009 | Model add/delete permission restricted to superuser | `agent-001` | `accepted` | `medium` | Add/delete and provider API-key configuration paths are now correctly restricted to superuser, with ordinary-user guidance and no fake success feedback |
| TK-010 | GraphRAG resume compatibility restoration after merge mismatch | `agent-B` | `accepted` | `high` | Resume summary runtime chain, Redis compatibility, and dataset GraphRAG resume/regenerate UI have now been restored; local Docker runtime is up again |
| TK-011 | Full-surface Chinese UI i18n audit and remediation | `agent-004` | `dispatched` | `high` | Full browser-based audit required across every page, dropdown, modal, and tooltip to repair raw keys, garbled Chinese, and missing localized labels |

## Ticket Notes

- `TK-001` was dispatched by `agent-x` to `agent-a` and has passed acceptance.
- `TK-002` was dispatched by `agent-x` to `agent-001` and has passed acceptance.
- `TK-003` was redefined after blockage review. After two rework rounds, the final accepted scope now includes backend fixed-label validation, persistent manual labeling, list filtering, and corrected locale-backed menu text for the labeling entry.
- `TK-004` was dispatched by `agent-x` to `agent-002`, fixed at the code level, and accepted with residual environment limitations noted in the acceptance record.
- `TK-005` was dispatched by `agent-x` to `agent-003` as a focused security remediation for the penetration-test finding on system prompt leakage. After two rework rounds, the accepted scope now includes agent-path hardening, ordinary chat-path hardening, prompt-field stripping on user-facing responses, and runtime regression coverage for the ordinary no-KB fallback path.
- `TK-009` was dispatched by `agent-x` to `agent-001` and accepted after two rework rounds. The final accepted scope closes both backend and frontend permission gaps for model add/delete and provider API-key configuration.
- `TK-010` was dispatched by `agent-x` to `agent-B` as a GraphRAG infrastructure restoration ticket and is now accepted after rework. The final accepted scope restores startup compatibility, Redis-backed resume summary handling, and the dedicated GraphRAG resume/regenerate UI path.
- `TK-011` was dispatched by `agent-x` to `agent-004` as a full-surface Chinese UI remediation ticket. This ticket requires browser-based inspection of every reachable page, dropdown, modal, and tooltip before acceptance.
- `TK-006` was dispatched by `agent-x` to `agent-B` as the first infrastructure phase for chat retrieval optimization. After two rework rounds and rebuilt-image runtime verification, this ticket is now accepted: `Thinking` keeps visible progress, no longer crashes on `GatheringFuture` during sub-query execution, and non-thinking graph-enabled chat returns visible graph evidence.
- `TK-007` was dispatched by `agent-x` to `agent-02` as a corrective follow-up after local runtime verification on `feature/security-hardening`. After rebuilt-image runtime verification, this ticket is now accepted: admin reset, ordinary-user self-service password change, lock-state visibility, lock guidance, and admin unlock all worked in the local Docker environment.
- `TK-008` is dispatched by `agent-x` to `agent-B` as a focused UI follow-up after `TK-006`. The change must optimize graph community-summary readability by default-collapsing long summary text, preserving click-to-expand full content, and keeping entities/relations easy to scan.
- `TK-008` is now accepted after rebuilt-image verification. The graph-evidence card keeps community summary available, and now collapses both the community-summary block and the combined entity/relation block by default with explicit expand/collapse controls.

## Flow Rules

- Assignees must update their work-order status before asking `agent-x` for acceptance.
- Assignees must add a completion record under their own `project-work/<agent>/` folder.
- `agent-x` is responsible for test acceptance, pass/fail judgment, and final close-out notes.
- If execution reveals a broader hidden scope, the assignee must report blockage instead of silently expanding the change.
