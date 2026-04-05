# TK-005 Acceptance

- Ticket ID: `TK-005`
- Reviewed By: `agent-x`
- Acceptance Time: `2026-04-04 23:59:00 +08:00`
- Result: `accepted`

## Reviewed Scope

Accepted remediation scope includes:

1. agent-path prompt leakage hardening
2. ordinary chat-path prompt leakage hardening
3. prompt-field stripping on user-facing responses
4. regression strengthening for ordinary no-KB runtime path

## Reviewed Files

- `common/prompt_security.py`
- `agent/component/llm.py`
- `agent/component/agent_with_tools.py`
- `api/db/services/dialog_service.py`
- `api/db/services/conversation_service.py`
- `api/apps/sdk/session.py`
- `test/unit/test_prompt_security_remediation.py`
- `project-work/agent-003/2026-04-04-TK-005-completion.md`
- `project-work/agent-003/2026-04-04-TK-005-rework-01-completion.md`
- `project-work/agent-003/2026-04-04-TK-005-rework-02-completion.md`

## Acceptance Notes

1. Ordinary chat now injects confidentiality rules in both `async_chat_solo` and `async_chat`.
2. Prompt-extraction attempts are intercepted on the ordinary chat path before normal generation proceeds.
3. The previous runtime blocker in `async_chat_solo` was removed by accepting and forwarding `**kwargs`.
4. User-facing response cleaning for the `prompt` field remains in place.
5. Runtime regression coverage now executes the ordinary no-KB fallback path rather than relying only on source-string checks.

## Verification Performed

1. Manual code review of the final remediation chain: **PASS**
2. Python compile check for modified runtime files: **PASS**
3. Direct runtime execution of ordinary no-KB regression helpers: **PASS**

## Residual Limits

1. `pytest` is not available in the current environment, so the repository test runner was not executed end-to-end.
2. The exact external penetration-test route appears to include outer-layer application wiring that is outside this repository, so final deployment validation should still include one real request-path retest.

## Final Judgment

`TK-005` is accepted. The in-repo remediation now covers both agent and ordinary chat paths, and the previously reported ordinary no-KB runtime breakage has been resolved.
