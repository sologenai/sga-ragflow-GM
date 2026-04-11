# 2026-04-10 TK-009 Review Round 2

## Review Result

- Ticket: `TK-009`
- Reviewer: `agent-x`
- Result: `rework required`
- Review Date: `2026-04-10`

## Primary Finding

The backend add-path permission gap is now closed, but the frontend add guidance is still incomplete on an existing provider/API-Key path.

Current remaining issue:

- file: `web/src/pages/user-setting/setting-model/components/modal-card.tsx`
- the provider-level `API-Key` / add-model button on an already-added provider still calls `clickApiKey(item.name)` directly
- there is no superuser guard on that click path

So an ordinary user can still:

1. open the API-Key/provider configuration modal from an existing provider card
2. attempt to save
3. hit a backend permission denial
4. not receive the required immediate “contact superuser” guidance at the entry point

## Why This Blocks Acceptance

The ticket required both:

- backend permission enforcement
- frontend ordinary-user guidance for add/delete attempts

Delete-side guidance is already present.
Add-side guidance is only partially present today:

- available-model add entry is guarded
- existing provider/API-Key entry is not

That means the UI still contains an add/configuration path where ordinary users are not handled with the intended product guidance.

## What Is Already Good

These parts now look correct and should be preserved:

- `/add_llm` superuser restriction
- `/delete_llm` superuser restriction
- `/delete_factory` superuser restriction
- `/set_api_key` superuser restriction
- no-op delete no longer returns success
- ordinary-user delete guidance
- fake delete success removed

## Required Rework Focus

Keep this rework small:

1. add the same ordinary-user guidance to the existing provider/API-Key entry path on model cards
2. ensure ordinary users do not enter an add/configuration modal from that path without being told to contact superuser
3. add self-test coverage for this exact UI path
