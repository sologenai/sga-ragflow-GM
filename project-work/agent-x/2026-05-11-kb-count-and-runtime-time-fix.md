# 2026-05-11 KB Count And Runtime Time Fix

## Context

User reported two regressions from the remote environment:

- Dataset sidebar showed `481 files`, while the document list pagination showed `567`.
- The previously required "current time awareness" in chat no longer behaved consistently, and needed to cover both chat assistants and agents.

## Root Cause

- The sidebar reads `Knowledgebase.doc_num`, which is a cached counter.
- The document list reads a live `DocumentService.get_by_kb_id(...)` count.
- After sync/import/delete paths, `Knowledgebase.doc_num` can drift from the live document count.
- The dataset detail React Query key did not include `knowledgeBaseId`, so switching datasets could also reuse stale detail data.
- Current time awareness was not implemented through a shared runtime prompt layer. Plain chat and agent LLM components had separate system prompt construction paths.

## Fix

- Added `DocumentService.get_count_by_kb_id(...)` using the same document/file join basis as the list endpoint.
- The KB detail endpoint now repairs and returns `doc_num` from the live count when a mismatch is detected.
- The frontend dataset detail query key now includes `knowledgeBaseId`.
- Added `common.prompt_runtime.append_current_time_context(...)`.
- Injected runtime current time into:
  - chat without KB: `async_chat_solo`
  - chat with KB/retrieval: `async_chat`
  - agent LLM component: `agent.component.llm.LLM._prepare_prompt_variables`

## Validation

- `python -m py_compile common\prompt_runtime.py api\db\services\document_service.py api\apps\kb_app.py api\db\services\dialog_service.py agent\component\llm.py`
- `python -m pytest -q test\unit_test\common\test_prompt_runtime.py`
- `python -m pytest -q test\unit_test\common\test_prompt_runtime.py test\unit_test\graphrag\test_graphrag_task_monitor_summary.py`
- `npm.cmd run build`
- `git diff --check`

## Deployment Note

This does not mutate stored user prompts. Current time is appended only at model-call runtime. Default timezone is `Asia/Shanghai`; it can be overridden with `RAGFLOW_PROMPT_TIMEZONE`.
