# 2026-04-05 TK-007 Acceptance

## Ticket

- Ticket ID: `TK-007`
- Assignee: `agent-02`
- Reviewer: `agent-x`
- Result: `accepted`
- Acceptance Date: `2026-04-05`

## Acceptance Conclusion

This ticket is accepted after rebuilt-image runtime verification.

I did not find a blocking functional issue in the delivered scope.

## What Was Verified

### 1. Password convention is now aligned with the active login chain

Reviewed in:

- `admin/server/services.py`
- `api/apps/user_app.py`
- `admin/server/auth.py`
- `api/db/services/user_service.py`

Confirmed outcome:

- active login still authenticates against `hash(plain password)`
- admin create user now validates via decoded plain text and stores plain text into the existing hash writer
- admin reset now validates/comparses transport input but compares and stores plain text
- personal-settings password change now verifies the real current plain password and stores the new plain password
- registration and forget-password reset now also store plain text into the existing hash writer
- default superuser initialization remains compatible with the same convention

### 2. Admin unlock capability is now present end-to-end

Reviewed in:

- `admin/server/services.py`
- `admin/server/routes.py`
- `web/src/utils/api.ts`
- `web/src/services/admin-service.ts`
- `web/src/services/admin.service.d.ts`
- `web/src/pages/admin/users.tsx`

Confirmed outcome:

- admin user listing now exposes `is_locked`
- backend unlock action exists at `PUT /api/v1/admin/users/<username>/unlock`
- unlock clears both Redis keys:
  - `login_attempts:<normalized_email>`
  - `login_lock:<normalized_email>`
- admin UI now has a lock-state column and a one-click unlock action for locked users

### 3. Lock message guidance is corrected

Reviewed in:

- `api/apps/user_app.py`
- `admin/server/auth.py`

Confirmed outcome:

- locked-login message now explicitly tells the user to contact an administrator for unlock

### 4. Rebuilt-image runtime verification passed

Runtime checked against local Docker image `ragflow-custom:tk006-tk007-r1`.

Confirmed outcome:

- admin reset of `jerrylin@sologenai.com` succeeded
- the reset password could be used to log in immediately
- the same ordinary user then changed password through `/v1/user/setting` successfully
- logging in with the old password failed after self-service change
- logging in with the new password succeeded
- repeated bad logins produced the expected `Please contact an administrator to unlock it` message
- admin users list exposed `is_locked=true` while the user was locked
- admin unlock succeeded and login worked again afterward

### 5. Regression coverage was added

Reviewed in:

- `test/unit_test/admin/test_admin_user_password_update.py`
- `test/unit_test/api/test_user_app_password_and_lock_contract.py`

Confirmed outcome:

- focused regression coverage exists for admin create/reset and unlock behavior
- user-app coverage is partly contract-style rather than full runtime execution, but it still guards the intended wiring

## Residual Risks

- Current environment still does not have `pytest`, so the new tests were not executed end-to-end here.
- The rebuilt-image runtime verification used API-level flows rather than a browser automation harness, although it exercised the real deployed backend and the rebuilt frontend bundle was included in the image.
- Historically corrupted password hashes are not auto-repaired by this ticket; those accounts still need one corrective password reset or reset-flow rewrite after deployment.

## Final Judgment

`TK-007` is accepted.
