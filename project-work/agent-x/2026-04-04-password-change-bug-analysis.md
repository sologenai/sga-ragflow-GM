# 2026-04-04 Password Change Bug Analysis

## Background

Customer feedback indicates that password modification is failing in one or both of these entry points:

- Admin UI password reset
- Personal settings password change

Because this issue has happened before, it needs a written root-cause record in addition to a work order.

## Code-Level Findings

### 1. Admin password reset runs on a separate admin server

The admin UI does not call `api/apps/user_app.py`.

It calls the independent admin server on port `9381`, as evidenced by:

- `docker/.env`
- `docker/docker-compose.yml`
- `admin/server/routes.py`

Relevant route:

- `admin/server/routes.py`
- `PUT /api/v1/admin/users/<username>/password`

### 2. Root cause is in the admin password update service

The direct bug is in:

- `admin/server/services.py`
- `UserMgr.update_user_password`

Current logic does three different things with the password:

1. `decrypt(new_password)` returns the base64-encoded password string used by the web login chain
2. it decodes that base64 string to plain text only for password-strength validation
3. but it then uses the plain-text password in places where the system expects the base64 password form

Specifically:

- it compares `check_password_hash(usr.password, psw)` using plain text
- it persists `UserService.update_user_password(usr.id, psw)` using plain text

However, the rest of the system uses the base64 password representation for hashing and verification:

- user login in `api/apps/user_app.py`
- personal settings password change in `api/apps/user_app.py`
- forget-password reset in `api/apps/user_app.py`
- user creation in `admin/server/services.py`

## Impact Assessment

This bug can cause two layers of failure:

### Direct impact

If an administrator resets a password from the admin UI, the new password can be stored in the wrong format.

Result:

- the user may not be able to log in with the newly reset password

### Secondary impact

Once an account password has already been written in the wrong format by the admin reset flow, the personal settings password-change endpoint can also fail later.

Reason:

- the personal settings flow verifies the current password against the base64-based convention
- the corrupted password record no longer follows that convention

Result:

- the user may see a current-password error in personal settings even when entering the expected password

## Scope Judgment

This is a small, concrete bug, not an architecture-level redesign.

Primary repair scope should be:

- fix the comparison format in `admin/server/services.py`
- fix the persistence format in `admin/server/services.py`
- add a regression test to prevent recurrence

## Special Note For Operations

Code repair will prevent future corruption, but it does not automatically repair accounts whose passwords were already reset through the broken admin path.

Those historically affected accounts may need:

- one more password reset after the fix is deployed
- or another validated repair path confirmed during execution

This point must be called out again in the execution completion record and final acceptance note.
