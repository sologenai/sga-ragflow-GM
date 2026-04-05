# 2026-04-04 TK-003 Review Round 1

## Verdict

- Result: rejected for rework
- Reviewer: `agent-x`
- Review date: `2026-04-04`

## Findings

### 1. Frontend source currently contains syntax-breaking string literals

Files:

- `web/src/pages/datasets/dataset-source.ts:41`
- `web/src/pages/datasets/index.tsx:103`

Issue:

- the `未标注` default text was written with broken characters and is missing the closing quote in both places
- this is not only a display/encoding issue; it produces an unterminated string literal in source code

Impact:

- the page cannot be considered deliverable in its current state
- any real frontend build/parse step will fail on these files

### 2. Fixed-label semantics are not enforced on the backend yet

Files:

- `api/apps/kb_app.py:168-174`
- `api/db/services/knowledgebase_service.py:447-458`

Issue:

- `kb_label` is currently accepted as a free-form incoming field and written through the normal update/create path
- there is no backend validation restricting values to the fixed set:
  - `manual`
  - `chat_graph`
  - `news_sync`
  - `archive_sync`
  - empty value for unlabeled

Impact:

- this weakens the "fixed label" requirement
- invalid values can be stored in the database and then silently collapse to unlabeled in the UI

## Rework Required

`agent-a` must at minimum:

1. Repair the broken string literals in the frontend source.
2. Add backend validation for `kb_label` on create/update paths.
3. Re-check that manual labeling, display, persistence, and filtering still work after the fix.

## Acceptance Note

This round is not accepted.

The implementation direction is valid, but the current delivery must be corrected before final acceptance.
