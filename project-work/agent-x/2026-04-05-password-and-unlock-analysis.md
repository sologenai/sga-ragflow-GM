# 2026-04-05 Password and Unlock Analysis

## Context

Local runtime verification on the current working branch `feature/security-hardening` showed two live issues:

- password change is still broken in real usage
- the expected admin-side user unlock capability is not present

This analysis is written to prevent follow-up remediation from repeating the earlier incorrect conclusion.

## Branch Reality

- Current branch: `feature/security-hardening`
- Relative to `origin/main`: `0 behind / 715 ahead`

Conclusion:

- this is not a simple "did not merge main" problem
- the current branch already contains `origin/main` and many additional custom commits

## Verified Password Findings

### 1. Login flow still authenticates against plain text after decrypt

Observed in:

- `api/apps/user_app.py`
- `admin/server/auth.py`
- `api/db/services/user_service.py`

Current real behavior:

1. frontend sends RSA-encrypted password
2. backend `decrypt(...)` returns a base64-encoded password string
3. login path decodes that base64 to plain text
4. `UserService.query_user(...)` checks the stored hash against plain text

Implication:

- the storage convention used by active login paths is still "hash(plain password)"

### 2. Admin create/reset path currently uses the wrong representation

Observed in:

- `admin/server/services.py`

Current problematic behavior:

- admin create user currently passes base64 password into `create_new_user(...)`
- admin reset password currently compares/stores base64 password representation

Implication:

- a password created or reset by the admin UI can become incompatible with normal login

### 3. Personal settings password change path is also inconsistent

Observed in:

- `api/apps/user_app.py`

Current problematic behavior:

- current-password verification compares against `decrypt(request_data["password"])`, which is still base64 text
- new password persistence hashes `new_pwd_base64`

Implication:

- accounts stored with plain-password hashes fail current-password verification here
- accounts re-saved by this path can diverge from the active login convention

### 4. Default superuser initialization is a special-case path

Observed in:

- `admin/server/auth.py`

Current behavior:

- default superuser is initialized with plain `admin`

Implication:

- this explains the mixed behavior seen locally:
  - login can still work for the default superuser
  - personal-settings password change fails because that route verifies using the wrong representation

## Verified Unlock Findings

### 1. Login lock behavior exists

Observed in:

- `api/apps/user_app.py`
- `api/utils/web_utils.py`

Current behavior:

- failed logins increment Redis key `login_attempts:<email>`
- lock flag is stored in Redis key `login_lock:<email>`

### 2. Admin unlock capability does not exist in the current branch

Observed in:

- `admin/server/routes.py`
- `admin/server/services.py`
- `web/src/pages/admin/users.tsx`

Current absence:

- no user-list field exposes lock state
- no admin API exposes unlock action
- no admin UI button supports unlock

Conclusion:

- the current branch has "lock user after failed logins"
- but does not have the second half of the product requirement:
  - admin can see that the user is locked
  - admin can unlock the user with one action

## Corrective Direction

The next remediation must treat these as one combined issue:

1. unify password handling to the real active login convention
2. repair admin create/reset and personal-settings password change to that convention
3. restore the missing admin unlock capability
4. change the lock message so the user is guided to contact an administrator

## Recommended Scope

In scope:

- password format correction for admin create user
- password format correction for admin reset user password
- password format correction for personal-settings password change
- default superuser compatibility review
- admin unlock API
- admin lock-state visibility and unlock button
- regression tests for password and unlock behavior

Out of scope:

- authentication-system redesign
- replacing RSA/base64 transport protocol
- mass data migration without explicit validation

