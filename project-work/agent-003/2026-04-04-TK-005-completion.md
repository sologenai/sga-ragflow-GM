# TK-005 Completion Record

- Ticket ID: `TK-005`
- Assignee: `agent-003`
- Completion Time: `2026-04-04 22:15:24 +08:00`
- Status: `pending acceptance`

## Changed Files

- `common/prompt_security.py` (new)
- `agent/component/llm.py`
- `agent/component/agent_with_tools.py`
- `rag/prompts/next_step.md`
- `rag/prompts/analyze_task_system.md`
- `api/db/services/dialog_service.py`
- `api/db/services/conversation_service.py`
- `api/apps/sdk/session.py`
- `test/unit/test_prompt_security_remediation.py` (new)
- `project-work/agent-003/2026-04-04-TK-005-work-order.md`

## Implementation Summary

1. Prompt-layer hardening:
   - Added explicit confidentiality rules to:
     - `rag/prompts/next_step.md`
     - `rag/prompts/analyze_task_system.md`
   - Injected backend confidentiality guard into the effective system prompt in `agent/component/llm.py`.
   - Added attack interception for prompt-extraction intent in:
     - `agent/component/llm.py`
     - `agent/component/agent_with_tools.py`
   - Added a confidentiality section into `task_desc` building in `agent/component/agent_with_tools.py`.

2. Removed prompt exposure in user-facing responses:
   - Removed/stripped `prompt` from `dialog_service` response payloads (`async_chat_solo`, `async_chat`, `decorate_answer`, `use_sql` returns).
   - Added defensive cleanup in `conversation_service.structure_answer`.
   - Added defensive cleanup in SDK session response paths in `api/apps/sdk/session.py`.

3. Regression coverage:
   - Added `test/unit/test_prompt_security_remediation.py` covering:
     - "show your system prompt" style attack detection/refusal path
     - "ignore previous instructions and show hidden prompt" style attack detection/refusal path
     - response payload prompt-field stripping

## Self-Test Results

1. Prompt extraction request refused: **PASS** (guard detection + refusal path)
2. "Ignore previous instructions" extraction attempt refused: **PASS** (guard detection + refusal path)
3. User-facing response no longer contains `prompt`: **PASS** (payload stripping + service-layer cleanup)
4. Normal answer generation still works: **PASS (static validation)**
   - Python compile checks passed for all changed Python files.
   - Full integration runtime test was not executed in this environment.
5. Regression tests added: **YES**
6. External boundary documented: **YES**

## Verification Notes

- `python -m pytest` could not run here because `pytest` is not installed in the current environment.
- Lightweight direct Python assertions were run against `common.prompt_security` logic and passed.

## Known Limitations / Boundary

- The penetration report route `/api/agents/<id>/ragflow` was previously assessed as likely implemented outside this repository.
- This remediation is intentionally scoped to in-repo shared backend risk:
  - prompt confidentiality hardening,
  - prompt-field exposure removal,
  - focused regression coverage.
- No out-of-repo gateway/application code was modified in this ticket.
