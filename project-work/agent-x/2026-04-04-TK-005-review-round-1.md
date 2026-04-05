# 2026-04-04 TK-005 Review Round 1

## Verdict

- Result: rejected for rework
- Reviewer: `agent-x`
- Review date: `2026-04-04`

## Findings

### 1. Ordinary chat prompt path is still not hardened against prompt-extraction requests

Files:

- `api/db/services/dialog_service.py:244`
- `api/db/services/dialog_service.py:495`
- `api/db/services/dialog_service.py:500`
- `common/prompt_security.py`
- `agent/component/llm.py:159`

Issue:

- this ticket added confidentiality-rule injection and attack interception for the agent-component path
- however, the ordinary chat path in `dialog_service` still sends `prompt_config["system"]` directly to the chat model
- there is no corresponding `append_prompt_confidentiality_rules(...)` usage in `dialog_service`
- there is also no prompt-extraction interception on the normal chat request path

Impact:

- the reported agent path is better protected
- but ordinary chat assistants in this repository can still rely only on their original prompt text
- that means prompt-leakage risk is reduced but not fully closed in the shared in-repo chat backend

## Acceptance Note

This round is not accepted.

The current delivery is close and the direction is correct:

- agent path hardening is in place
- prompt-field exposure cleanup is in place
- regression utility coverage exists

But one more controlled follow-up fix is required so the ordinary chat prompt path receives the same baseline confidentiality hardening.

## Rework Required

`agent-003` must at minimum:

1. apply confidentiality-rule injection to the ordinary chat system prompt path in `dialog_service`
2. decide whether the normal chat path also needs prompt-extraction interception, and implement the minimum safe version
3. extend regression coverage to include the chosen normal-chat hardening behavior or document the boundary more explicitly if interception is intentionally limited
