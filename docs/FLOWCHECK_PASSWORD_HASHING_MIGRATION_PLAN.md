# FlowCheck+ Password Hashing Migration Plan

## Current Findings

F-03 in `docs/FLOWCHECK_SECURITY_HOTFIX_PLAN.md` identifies legacy password hashing that uses unsalted SHA-256. This is not suitable for production authentication because it is fast, unsalted, and vulnerable to offline cracking if hashes are exposed.

The modular auth stack already uses bcrypt via `modules/rechnungsverarbeitung/src/auth/jwt_auth.py` and `modules/rechnungsverarbeitung/src/invoices/services/user_service.py`. The migration should therefore align legacy password creation, login, and reset flows with the modular bcrypt behavior instead of introducing a second password-hashing standard.

## Affected Files / Functions

Known legacy touchpoints from the security review:

- `database.py` create/login/reset paths around lines 995, 1019, 1109, 1133, and 1882.
- `web/app.py` registration path around line 1473.

Known modular bcrypt reference points:

- `modules/rechnungsverarbeitung/src/auth/jwt_auth.py`
- `modules/rechnungsverarbeitung/src/invoices/services/user_service.py`

Line numbers may drift; implementation should search for SHA-256 password hashing and password update code paths rather than relying only on fixed line numbers.

## Target State

- All newly written password hashes use bcrypt.
- Existing bcrypt hashes continue to verify without modification.
- Existing legacy SHA-256 hashes continue to work temporarily, but only through a compatibility verifier.
- On successful login with a legacy SHA-256 hash, the password is immediately rehashed to bcrypt and persisted.
- Reset-password and registration flows always write bcrypt hashes.
- No plaintext password or temporary password is logged or returned.

## Migration Strategy

Use a backward-compatible verifier first, then progressively remove SHA-256 support after enough successful transparent upgrades and monitoring.

1. Introduce shared helper functions in the legacy auth path:
   - `is_bcrypt_hash(value: str) -> bool`
   - `is_legacy_sha256_hash(value: str) -> bool`
   - `verify_password_compatible(password: str, stored_hash: str) -> tuple[bool, bool]`
   - `hash_password_bcrypt(password: str) -> str`
2. Update legacy login flows to:
   - detect bcrypt hashes and verify with bcrypt.
   - detect legacy SHA-256 hashes and verify with the old comparison.
   - if legacy verification succeeds, replace the stored hash with bcrypt.
3. Update legacy reset-password flows to write bcrypt only.
4. Update legacy registration flows to write bcrypt only.
5. Keep the modular stack unchanged except for any shared helper reuse if it is clearly low-risk.

## Backward-Compatible Verification Approach

Detection rules:

- bcrypt hashes are detected by prefix, for example `$2a$`, `$2b$`, or `$2y$`.
- legacy SHA-256 hashes are detected by a strict 64-character lowercase/uppercase hexadecimal pattern.
- any unknown hash format fails closed and logs only non-sensitive metadata.

Verification behavior:

- If `stored_hash` is bcrypt:
  - verify using bcrypt.
  - do not rewrite unless a later policy requires cost-factor upgrades.
- If `stored_hash` is legacy SHA-256 hex:
  - compute the legacy SHA-256 hash of the submitted password.
  - compare using a constant-time comparison.
  - if verification succeeds, write a new bcrypt hash for the same plaintext password.
- If verification fails:
  - return the same generic login failure as today.
  - do not disclose whether the user exists or which hash format was stored.

## Reset-Password Behavior

All newly generated or submitted reset passwords must be stored with bcrypt.

The reset flow must not:

- write SHA-256 hashes.
- log temporary passwords.
- return temporary passwords in API responses.
- reveal whether a user exists beyond the existing generic response model.

## Registration Behavior

All new registrations must store bcrypt hashes.

The registration path in `web/app.py` should be changed from legacy SHA-256 hashing to the same bcrypt helper used by login/reset compatibility. Modular registration in `user_service.py` already uses bcrypt and should remain the reference behavior.

## Risk Analysis

### Login Lockout

The highest risk is locking out users whose stored hashes are misclassified. Mitigation: use strict detection rules, preserve SHA-256 verification during the first patch, and test both hash formats against realistic database rows.

### Double Hashing

Double hashing can occur if a bcrypt hash is treated as plaintext or if an already hashed value is passed into a hashing function. Mitigation: hash only submitted plaintext passwords, never stored hashes, and keep helper names explicit.

### DB Schema Compatibility

bcrypt hashes are longer than SHA-256 hex hashes. Verify that the relevant password column can store bcrypt strings (typically around 60 characters, sometimes longer depending on implementation). If the column is too narrow, widen the column before writing bcrypt.

### Legacy vs Modular User Tables

Legacy and modular auth may not share the same table or lifecycle. Do not assume one migration covers both. Patch legacy flows explicitly and keep modular bcrypt behavior intact. A user-table merge is a separate architectural migration, not part of the first security hotfix.

## Test Plan

- bcrypt login:
  - seed a user with a bcrypt hash.
  - verify correct password succeeds.
  - verify stored hash remains bcrypt.
- legacy SHA login with transparent upgrade:
  - seed a user with a 64-character SHA-256 hash.
  - verify correct password succeeds.
  - verify the stored hash is replaced with bcrypt after login.
- wrong password:
  - verify wrong password fails for bcrypt and legacy SHA-256 users.
  - verify no hash rewrite happens on failure.
- reset password writes bcrypt:
  - trigger reset flow.
  - verify the stored password hash has a bcrypt prefix.
  - verify no temporary password is logged or returned.
- registration writes bcrypt:
  - register a new user through the legacy registration path.
  - verify the stored password hash has a bcrypt prefix.
  - verify login works with the new bcrypt hash.

## Rollout Plan

1. Code patch:
   - add compatibility helpers.
   - update legacy login, reset, and registration paths.
   - keep modular bcrypt code unchanged.
2. Local backup:
   - back up the local database before testing.
   - record row counts and sample hash-format counts without exposing hash values.
3. Staging:
   - deploy to staging with copied or synthetic representative users.
   - test bcrypt login, legacy login upgrade, reset, and registration.
4. Production deploy:
   - back up the production database.
   - deploy during a low-traffic window.
   - do not run a bulk rewrite in the first patch.
5. Monitor:
   - failed login rate.
   - reset-password errors.
   - registration errors.
   - count of remaining legacy SHA-256 hashes over time.

## Rollback Plan

- Revert the code patch if login failures spike or reset/registration breaks.
- Restore the pre-deploy database backup only if bcrypt writes corrupt data or a schema issue prevents auth recovery.
- If some users were already transparently upgraded to bcrypt, rollback code must still understand bcrypt or those users may be locked out. Prefer fixing forward unless the failure is severe.

## Non-Goals

- No forced password reset in the first patch.
- No schema rewrite unless column width makes bcrypt storage impossible.
- No user-table merge yet.
- No bulk password rehash job in the first patch.
- No changes to unrelated auth architecture or OAuth/SSO behavior.
