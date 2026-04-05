# TK-005 Rework 02 Completion

- Ticket ID: `TK-005`
- Rework Round: `02`
- Assignee: `agent-003`
- Completion Time: `2026-04-04 23:46:42 +08:00`
- Status: `pending acceptance`

## Scope

Focused hotfix only for review-round-2 findings:

1. fix potential runtime blocker in ordinary no-KB chat fallback path
2. strengthen regression from source-string wiring checks to runtime path execution

## Changed Files

- `api/db/services/dialog_service.py`
- `test/unit/test_prompt_security_remediation.py`

## Implementation

1. Ordinary no-KB chat path wiring safety
   - Updated `async_chat_solo` signature to accept `**kwargs`.
   - Updated `async_chat` fallback call to pass through `**kwargs` into `async_chat_solo`.
   - This removes the undefined-kwargs risk and keeps fallback path stable for ordinary chats without KB/Tavily.

2. Runtime regression strengthening
   - Kept existing wiring assertion test.
   - Added runtime tests that execute `async_chat_solo` extracted from source with minimal stubs:
     - `test_async_chat_solo_no_kb_runtime_path`
       - verifies normal no-KB answer path works
       - verifies confidentiality rules are injected into system prompt
       - verifies `prompt` field is absent in output
     - `test_async_chat_solo_prompt_leakage_refusal_runtime`
       - verifies prompt-extraction attack returns refusal
       - verifies final payload still does not expose `prompt`

## Self-Check

1. Ordinary no-KB chat remains functional: **PASS**
2. Ordinary no-KB prompt-leakage refusal still active: **PASS**
3. Runtime regression now covers executed fallback path: **PASS**
4. Prompt-field stripping behavior remains intact: **PASS**

## Verification Notes

- `python -m pytest` remains unavailable in this environment because `pytest` is not installed.
- Executed validation:
  - Python compile check for modified files: **PASS**
  - Direct execution of all tests in `test_prompt_security_remediation.py` via Python import-and-call: **PASS**
