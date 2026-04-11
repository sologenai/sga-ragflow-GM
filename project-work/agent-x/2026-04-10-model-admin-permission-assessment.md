# 2026-04-10 Model Admin Permission Assessment

## Issue Summary

Current model-management behavior does not enforce the intended permission boundary:

- only superusers should be allowed to add models
- only superusers should be allowed to delete models or providers
- ordinary users should receive a clear guidance message instead of a fake success result

The current user-visible bug is:

- an ordinary user can click model delete in the UI
- the UI shows a success message
- the model is not actually deleted

## Findings

### 1. Frontend exposes add/delete actions to all users

The model-management UI currently renders provider delete and model delete actions without any superuser gating.

Relevant files:

- `web/src/pages/user-setting/setting-model/components/modal-card.tsx`
- `web/src/pages/user-setting/setting-model/hooks.tsx`

There is no current role check before:

- showing provider delete
- showing single-model delete
- opening model-add flows

### 2. Frontend reports success purely by `code === 0`

The delete hooks show a success toast whenever the backend returns `code === 0`.

Relevant file:

- `web/src/hooks/use-llm-request.tsx`

Current behavior:

- `useDeleteLlm` shows `message.success(...)` on `code === 0`
- `useDeleteFactory` does the same

This means a backend no-op still becomes a visible fake success on the frontend.

### 3. Backend delete endpoints do not enforce superuser-only access

Relevant file:

- `api/apps/llm_app.py`

Current `/delete_llm` and `/delete_factory` behavior:

- delete only where `TenantLLM.tenant_id == current_user.id`
- always return `get_json_result(data=True)`
- do not check `current_user.is_superuser`
- do not verify affected-row count

As a result, an ordinary user can reach the delete endpoint, hit a no-op delete, and still receive a success response.

### 4. Display scope and delete scope are inconsistent

Relevant files:

- `api/apps/llm_app.py`
- `api/db/services/tenant_llm_service.py`

`/my_llms` resolves configuration tenant through `_resolve_llm_tenant_id()`.
When global LLM is enabled, this can point to the admin tenant via `TenantLLMService.get_admin_tenant_id()`.

That means an ordinary user can see admin/global models, while delete still operates only on:

- `TenantLLM.tenant_id == current_user.id`

This mismatch explains the observed bug:

- visible model
- delete button available
- delete says success
- nothing is deleted

### 5. Add-model path requires the same restriction

Relevant files:

- `api/apps/llm_app.py`
- `web/src/pages/user-setting/setting-model/hooks.tsx`

The add-model path currently does not enforce a superuser-only rule either.
Because the product requirement is now explicit, add and delete should be hardened together in one ticket.

## Recommended Fix Direction

### Backend

Enforce permissions in the add/delete endpoints:

- only superusers can add models
- only superusers can delete a model
- only superusers can delete a provider

When an ordinary user attempts these actions, return an explicit permission error instead of `code === 0`.

Also stop returning success for delete no-ops:

- either return a permission error
- or return a clear "not found / not allowed" failure when affected rows are zero

### Frontend

Use the current logged-in user role to gate model-management actions.

The cleanest current role source is:

- `useFetchUserInfo()`

Relevant files:

- `web/src/hooks/use-user-setting-request.tsx`
- `web/src/interfaces/database/user-setting.ts`

Expected frontend behavior:

- ordinary users should not get a fake success toast
- ordinary users should see a clear message such as:
  - `需要新增模型，请联系超级管理员`
  - `需要删除模型，请联系超级管理员`

Product can choose one of these UI treatments:

- hide add/delete entry points for ordinary users
- keep the entry visible but disable it and show the guidance message on click

For this ticket, either treatment is acceptable as long as:

- only superusers can actually perform add/delete
- ordinary users get explicit guidance
- fake success is removed

## Ticket Recommendation

Open a dedicated follow-up ticket for `agent-001` covering:

- backend permission hardening for add/delete model/provider
- frontend superuser gating
- ordinary-user guidance messaging
- regression validation for both add and delete flows
