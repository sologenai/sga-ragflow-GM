# TK-007 Review Round 1

## Ticket

- Ticket ID: `TK-007`
- Reviewer: `agent-x`
- Review Time: `2026-04-05 17:05:00 +08:00`
- Result: `rework required`

## Review Trigger

Live browser-side verification after rebuilding the local Docker image showed that:

1. superuser self-service password change in the RAGFlow profile page now works
2. ordinary-user password handling is still not complete across real user-facing paths

This review focuses on the remaining ordinary-user self-service password-change issue.

## Findings

### 1. Admin-side reset and self-service password change are different paths

The following two paths are independent:

- admin resets another user's password in the admin user-management page
- the user changes their own password in the RAGFlow profile/settings page

The current failure is on the second path.

Relevant files:

- `web/src/pages/admin/users.tsx`
- `admin/server/routes.py`
- `admin/server/services.py`
- `web/src/pages/user-setting/profile/index.tsx`
- `web/src/pages/user-setting/profile/hooks/use-profile.ts`
- `api/apps/user_app.py`

### 2. Ordinary-user self-service password change can fail silently before the request is sent

The profile password modal currently uses a password schema that still inherits required profile fields from the broader base schema.

Observed consequence:

- the password modal is validating unrelated fields such as `userName` and `timeZone`
- those fields are not the actual intent of the password dialog
- ordinary users created from the admin side are especially likely to hit this because some of them still have empty or incomplete profile values
- when validation fails on hidden/unrelated fields, clicking `Save` appears to do nothing from the user's perspective

Relevant files:

- `web/src/pages/user-setting/profile/index.tsx`
- `web/src/pages/user-setting/profile/hooks/use-profile.ts`

### 3. User-facing feedback is insufficient for this failure mode

Because the failure can happen at the form-validation layer rather than the backend layer:

- no password-change request is sent
- no success message appears
- no backend error is returned
- the user experiences the dialog as unresponsive

This is not acceptable for a self-service account recovery surface.

## Review Judgment

`TK-007` must be reopened for rework.

The previously accepted admin reset / unlock improvements remain valuable, but the ticket is not complete until the ordinary-user self-service password-change modal behaves correctly and predictably.
