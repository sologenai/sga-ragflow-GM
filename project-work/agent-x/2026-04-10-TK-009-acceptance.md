# TK-009 Acceptance

- Ticket ID: `TK-009`
- Reviewed By: `agent-x`
- Acceptance Time: `2026-04-10 20:30:00 +08:00`
- Result: `accepted`

## Acceptance Conclusion

This ticket is accepted.

The model-management add/delete permission boundary is now coherent across backend and frontend:

- only superusers can add provider/model configuration
- only superusers can delete a model or provider
- ordinary users now receive explicit guidance to contact the superuser
- failed delete attempts no longer surface as fake success

## Verification Performed

### 1. Backend permission verification

Confirmed superuser restriction is enforced on all relevant write paths in:

- `api/apps/llm_app.py`

Verified routes:

- `/add_llm`
- `/delete_llm`
- `/delete_factory`
- `/set_api_key`

Also confirmed delete no-op now returns non-success instead of unconditional success.

### 2. Frontend behavior verification

Confirmed role-aware add/delete handling is wired through:

- `web/src/pages/user-setting/setting-model/index.tsx`
- `web/src/pages/user-setting/setting-model/components/modal-card.tsx`
- `web/src/pages/user-setting/setting-model/hooks.tsx`
- `web/src/hooks/use-llm-request.tsx`
- `web/src/hooks/use-user-setting-request.tsx`

Confirmed the final remaining gap is now closed:

- the existing provider-card `API-Key` button now checks superuser before entering the modal path
- ordinary-user clicks show add-side guidance immediately
- superuser behavior remains unchanged

### 3. Message/result verification

Confirmed:

- ordinary-user guidance copy exists in locale files
- delete success toast is conditioned on real successful delete
- blocked add/delete requests do not produce fake success

## Accepted Behavior

- superuser can continue to use model add/provider configuration paths
- superuser can delete single models
- superuser can delete providers
- ordinary users are blocked from add/delete write paths
- ordinary users are told to contact the superuser
- no-op or blocked delete attempts do not show success

## Residual Notes

- This acceptance is based on code-path verification plus targeted lint/compile evidence from the assignee, not full browser multi-role live automation.
- The ticket intentionally did not redesign edit/enable/disable permissions.

## Final Judgment

`TK-009` is accepted.
