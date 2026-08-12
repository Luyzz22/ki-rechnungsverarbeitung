# PostgreSQL Schema Lifecycle Boundary

## Decision

The legacy runtime and the modular SQLAlchemy/Alembic stack must not own the same physical `invoices` table.

- `database.py` remains the owner of the legacy `invoices` table. Its tenant/user domain is integer-based.
- The modular SQLAlchemy stack owns `processing_invoices` and `processing_invoice_events`. Its tenant domain is string-based.
- Alembic revision `002_namespace_modular_invoice_tables` separates the modular tables and refuses to rename a table that looks like the legacy runtime schema.

## Why this is required

Before this change, Alembic revision `001_initial` created `invoices.tenant_id` as `String(128)`, while the legacy runtime expected an integer tenant/user domain. Running both schema lifecycles against one PostgreSQL database could therefore create a type-incompatible table that still looked superficially valid.

This is a tenant-isolation and migration-integrity risk. The remediation is intentionally fail-closed: ambiguous existing databases require an explicit offline assessment and migration plan. No automatic cast, user renumbering, FK rewrite, or destructive repair is performed.

## Cutover invariant

A PostgreSQL cutover is not approved merely because Alembic reaches `head`. Before production use:

1. Run the existing read-only PostgreSQL ID-domain assessment.
2. Verify `users.id`, `jobs.user_id`, `subscriptions.user_id`, and legacy invoice ownership are type-consistent.
3. Verify both modular tables exist under the `processing_*` names after Alembic upgrade.
4. Exercise login, upload, invoice listing, tenant-negative tests, approval, export, and AI-policy gates on staging.
5. Perform backup/restore and rollback rehearsal before setting the production `DATABASE_URL`.

## Compliance relevance

This boundary supports data protection by design and the effectiveness testing of technical controls, particularly tenant isolation and controlled schema change. It is relevant to GDPR Articles 25 and 32(1)(b)/(d), and to NIS2 Article 21(2)(e)/(f) where NIS2 applies.
