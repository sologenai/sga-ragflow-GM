# 2026-04-04 TK-005 Review Round 2

## Verdict

- Result: rejected for rework
- Reviewer: `agent-x`
- Review date: `2026-04-04`

## Findings

### 1. Ordinary no-KB chat path now references undefined `kwargs` and will fail at runtime

File:

- `api/db/services/dialog_service.py:236`

Issue:

- `async_chat_solo(dialog, messages, stream=True)` does not accept `**kwargs`
- but the function now executes `request_retrieval_mode = kwargs.get("retrieval_mode")`
- this causes a `NameError` when the function is called

Impact:

- `async_chat_solo(...)` is the ordinary fallback path used when a dialog has no knowledge base and no Tavily key
- that means normal chat assistants without KBs can fail before producing any answer
- this is a functional blocker, not only a security hardening gap

### 2. The new wiring test does not exercise the runtime path strongly enough

File:

- `test/unit/test_prompt_security_remediation.py:61`

Issue:

- the new test only checks that target strings exist in source text
- it does not catch runtime issues such as the undefined `kwargs` reference introduced in `async_chat_solo`

Impact:

- the added regression check is useful as a wiring assertion
- but it was not strong enough to guard the actual runtime path touched in this rework

## Acceptance Note

This round is not accepted.

The ordinary chat hardening direction is correct, but the current delivery breaks the normal no-KB chat path and must be corrected before acceptance.

## Rework Required

`agent-003` must at minimum:

1. remove or correctly wire the undefined `kwargs` usage in `async_chat_solo`
2. re-check the ordinary no-KB chat path after the fix
3. strengthen the regression coverage or direct self-check so this runtime issue would be caught next time
