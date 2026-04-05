# 2026-04-04 Model Single Delete Assessment

## Background

Current feedback from the project side:

- In the model management page, one provider can contain multiple models.
- The UI currently supports deleting an entire provider group.
- The UI does not provide a way to delete a single model under that provider.

This causes a management issue:

- If only one model under a provider needs to be removed, the administrator currently has to delete the whole provider configuration.
- This is too coarse and can accidentally remove other models that should remain available.

## Current Code Findings

After checking the current implementation, the conclusion is:

- Backend single-model delete capability already exists.
- Frontend API service already exposes the single-model delete endpoint.
- Frontend React hook already wraps the single-model delete action.
- The missing part is mainly the management page UI entry.

### Backend

Single model delete endpoint already exists in:

- `api/apps/llm_app.py`

Current route:

- `/delete_llm`

Request requirements:

- `llm_factory`
- `llm_name`

Behavior:

- Delete only the specified model under the specified provider for the current tenant.

Provider-level delete also exists separately:

- `/delete_factory`

So the backend already distinguishes:

- delete one model
- delete the whole provider

### Frontend Service Layer

Single model delete API already exists in:

- `web/src/services/user-service.ts`

Current exposed method:

- `delete_llm`

### Frontend Hook Layer

Single model delete hook already exists in:

- `web/src/hooks/use-llm-request.tsx`

Current hook:

- `useDeleteLlm`

It already handles:

- calling `delete_llm`
- refreshing model list queries
- showing delete success message

### Current UI Gap

The main model management card is in:

- `web/src/pages/user-setting/setting-model/components/modal-card.tsx`

Current behavior:

- Provider header has a delete button.
- That button deletes the whole provider by calling provider delete flow.
- Each model row currently only has:
  - edit button for local providers
  - enable/disable switch
- Each model row does not have a delete button.

There is also already a page-level helper hook for single-model delete in:

- `web/src/pages/user-setting/setting-model/hooks.tsx`

Current helper:

- `useHandleDeleteLlm`

Therefore, the business logic is already prepared and only not connected into the row UI.

## Project Manager Conclusion

This issue is not a backend capability gap.

It is primarily a frontend management-page enhancement:

- expose a delete button on each model row
- connect that button to the existing single-model delete flow
- keep the provider-level delete button unchanged

## Recommended Implementation Strategy

Use the minimum-change approach.

### Scope

Recommended scope:

- Only modify the model management frontend page
- Reuse existing API and hooks
- Do not change database structure
- Do not change backend interface design

### Expected UI Change

For each model row under a provider:

- add a delete button
- show a delete confirmation dialog
- confirm text should clearly identify:
  - provider name
  - model name

Keep current provider-level delete button as-is for deleting the whole provider group.

### Suggested Files

Likely affected files:

- `web/src/pages/user-setting/setting-model/components/modal-card.tsx`
- `web/src/pages/user-setting/setting-model/hooks.tsx`

Possible minor support updates if needed:

- locale text files under `web/src/locales/`

## Acceptance Focus

Acceptance should verify:

- Deleting one model removes only that model.
- Other models under the same provider remain intact.
- Provider delete still works as before.
- Enable/disable switch still works as before.
- Local model edit button still works as before.
- Query refresh after deletion is correct.
- No obvious layout or interaction regression appears in the model management page.

## Risk Assessment

Risk level:

- Low

Reason:

- backend capability already exists
- frontend hook already exists
- likely a small UI exposure change

Main risk points:

- accidental confusion between provider delete and model delete
- confirmation text not clear enough
- row action area becoming visually crowded

## PM Recommendation

This issue is suitable to open as an independent work order.

Recommended work order direction:

- "Add per-model delete action in model management page"

Recommended priority:

- Medium

Recommended implementation principle:

- minimum change
- frontend only if possible
- preserve existing provider delete behavior
