# TK-005 Rework 01 Completion

- Ticket ID: `TK-005`
- Rework Round: `01`
- Assignee: `agent-003`
- Completion Time: `2026-04-04 23:37:35 +08:00`
- Status: `pending acceptance`

## Scope

Focused follow-up only for review finding:

1. add normal-chat system prompt confidentiality hardening
2. add minimal prompt-extraction interception on normal chat path
3. add regression coverage for normal-chat wiring

## Changed Files

- `api/db/services/dialog_service.py`
- `test/unit/test_prompt_security_remediation.py`

## Implementation

1. Ordinary chat prompt hardening in `dialog_service`
   - `async_chat_solo(...)` now applies `append_prompt_confidentiality_rules(...)` before model invocation.
   - `async_chat(...)` now applies `append_prompt_confidentiality_rules(...)` when building the system prompt for the main chat generation path.

2. Ordinary chat prompt-extraction interception
   - `async_chat_solo(...)` checks the latest user request with `is_prompt_leakage_attempt(...)`, returns `prompt_leakage_refusal()` and exits early if matched.
   - `async_chat(...)` performs the same early check on `latest_user_question` before retrieval/generation and exits with a refusal payload if matched.

3. Regression extension
   - Added `test_dialog_service_chat_path_hardening_wired()` in `test/unit/test_prompt_security_remediation.py`.
   - This test verifies normal-chat path wiring for:
     - confidentiality-rule injection
     - prompt-extraction attack check

## Self-Check

1. Normal chat system prompt path hardened: **PASS**
2. Normal chat extraction interception wired: **PASS**
3. Existing prompt-field stripping remains intact: **PASS** (no regression edits in stripping logic)
4. Added regression for normal-chat hardening: **YES**

## Verification Notes

- `python -m pytest` is still unavailable in current environment because `pytest` is not installed.
- Executed:
  - Python compile check for modified files: **PASS**
  - Direct assertion script validating `dialog_service` hardening wiring and attack matcher: **PASS**
