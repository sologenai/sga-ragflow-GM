# 2026-04-10 TK-009 Completion

## Ticket

- Ticket: `TK-009`
- Executor: `agent-001`
- Completion Time: `2026-04-10 19:47:16 +08:00`
- Result: `completed`
- Status: `pending acceptance`

## Changed Files

- `api/apps/llm_app.py`
- `api/db/services/tenant_llm_service.py`
- `web/src/pages/user-setting/setting-model/components/modal-card.tsx`
- `web/src/pages/user-setting/setting-model/hooks.tsx`
- `web/src/pages/user-setting/setting-model/index.tsx`
- `web/src/hooks/use-llm-request.tsx`
- `web/src/hooks/use-user-setting-request.tsx`
- `web/src/locales/en.ts`
- `web/src/locales/zh.ts`
- `project-work/agent-001/2026-04-10-TK-009-work-order.md`
- `project-work/agent-001/2026-04-10-TK-009-completion.md`

## Implementation Summary

1. Backend permission hardening (`api/apps/llm_app.py`)
   - Added explicit superuser enforcement for:
     - `/llm/add_llm`
     - `/llm/delete_llm`
     - `/llm/delete_factory`
   - Ordinary user now receives non-success response (`RetCode.PERMISSION_ERROR`) with clear guidance to contact superuser.
2. Backend delete result correctness
   - `/llm/delete_llm` now checks affected rows; zero-effect delete returns non-success (`RetCode.NOT_FOUND`).
   - `/llm/delete_factory` now checks affected rows; zero-effect delete returns non-success (`RetCode.NOT_FOUND`).
3. Tenant LLM service support (`api/db/services/tenant_llm_service.py`)
   - Added `delete_llm_by_tenant(...)` and `delete_factory_by_tenant(...)` to return concrete affected-row counts.
4. Frontend role-aware add/delete behavior
   - Added user-role helper `useModelAdminPermission()` in `use-user-setting-request.tsx` using current login info (`useFetchUserInfo`).
   - Added `useModelAdminGuard()` in setting-model hooks for unified add/delete guidance messages.
   - Add entry points now role-gated in `setting-model/index.tsx`:
     - ordinary user add attempt -> warning guidance message.
   - Delete actions now role-gated in `setting-model/hooks.tsx`:
     - ordinary user delete model/provider attempt -> warning guidance message.
   - Provider delete confirm dialog is suppressed for ordinary users; click directly shows guidance message.
5. Frontend fake-success prevention (`web/src/hooks/use-llm-request.tsx`)
   - Delete success toast and query invalidation now require both:
     - `code === 0`
     - `data === true`
   - Prevents success toast on non-success or zero-effect delete responses.
6. Guidance texts
   - Added locale messages:
     - `contactSuperuserToAddModel`
     - `contactSuperuserToDeleteModel`
   - Updated `en.ts` and `zh.ts`.
7. Scope control check
   - `enable/disable` and edit permission logic were not changed.
   - `web/src/interfaces/database/user-setting.ts` was reviewed and kept unchanged (existing `is_superuser` field is already sufficient).

## Self-Test Results

Test basis: code-path validation + static checks in current environment.

1. superuser add model: **pass**
   - `/add_llm` allows only when `current_user.is_superuser` is true.
2. superuser delete single model: **pass**
   - `/delete_llm` allows superuser and deletes by tenant+factory+model.
3. superuser delete provider: **pass**
   - `/delete_factory` allows superuser and deletes by tenant+factory.
4. ordinary user add model: **pass**
   - backend returns non-success permission error;
   - frontend add entry shows guidance message and blocks action.
5. ordinary user delete single model: **pass**
   - backend returns non-success permission error;
   - frontend delete handler shows guidance message and blocks action.
6. ordinary user delete provider: **pass**
   - backend returns non-success permission error;
   - frontend delete handler shows guidance message and blocks action.
7. ordinary user guidance message visibility: **pass**
   - add guidance and delete guidance messages are explicitly wired in role guards.
8. failed delete no longer shows fake success: **pass**
   - backend returns non-success for zero-effect delete;
   - frontend success toast requires `code===0 && data===true`.
9. non add/delete behavior not accidentally broken: **pass**
   - `enable/disable` and edit code paths remain unchanged.

## Verification Commands

- Backend syntax check:
  - `python -m py_compile api/apps/llm_app.py api/db/services/tenant_llm_service.py`
- Frontend targeted lint:
  - `.\node_modules\.bin\eslint.cmd src/pages/user-setting/setting-model/index.tsx src/pages/user-setting/setting-model/components/modal-card.tsx src/pages/user-setting/setting-model/hooks.tsx src/hooks/use-llm-request.tsx src/hooks/use-user-setting-request.tsx src/locales/en.ts src/locales/zh.ts --max-warnings 0`

## Known Limitations

- No live browser/API integration run was executed in this environment (results above are based on code-path and static checks).
- `set_api_key` endpoint was not changed in this ticket; this implementation follows the ticket’s required backend enforcement scope (`add_llm` / `delete_llm` / `delete_factory`).
