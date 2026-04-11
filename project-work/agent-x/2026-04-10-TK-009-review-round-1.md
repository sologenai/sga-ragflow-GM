# 2026-04-10 TK-009 Review Round 1

## Review Result

- Ticket: `TK-009`
- Reviewer: `agent-x`
- Result: `rework required`
- Review Date: `2026-04-10`

## Primary Finding

The ticket did not fully close the backend add-path permission boundary.

`/set_api_key` remains open to ordinary users:

- file: `api/apps/llm_app.py`
- route: `/set_api_key`

In the current model-management product flow, this is still a real provider/model configuration write path because it persists tenant LLM records for the selected provider.

That conflicts with the explicit ticket target:

- only superusers can add models

## Why This Blocks Acceptance

The work order explicitly required:

- backend must be the source of truth
- provider/API-key add entry must be checked if applicable
- ordinary users must not be able to add models

The current completion record marks `/set_api_key` as intentionally out of scope, but this path is still part of the effective add flow. That leaves a backend-side bypass open even though the frontend add entry is now gated.

## What Is Already Good

These parts look correct and can be preserved:

- superuser checks on `/add_llm`
- superuser checks on `/delete_llm`
- superuser checks on `/delete_factory`
- no-op delete no longer returns success
- frontend ordinary-user delete guidance
- fake delete success has been removed

## Required Rework Focus

Rework should stay narrow:

1. close backend ordinary-user access on `/set_api_key` if it remains a provider/model configuration write path
2. keep frontend add guidance aligned with the backend restriction
3. add explicit self-test coverage for ordinary-user provider/API-key add attempt
