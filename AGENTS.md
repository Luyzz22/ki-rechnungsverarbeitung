# Codex Agent Instructions (invoice-app)

## Scope / Workspace
- Workspace root is: `/var/www/invoice-app`
- Do **not** read/modify files outside this workspace unless explicitly instructed.
- Treat `/etc`, `/var/log`, `/home/*`, `/root`, and any backups as **out of scope**.

## Security / Secrets
- Never print, echo, log, or commit secrets (API keys, tokens, credentials).
- Never store secrets in repo files. Use Codex auth store + server-side protected locations only.
- If a secret is detected in output/files: stop, redact, rotate, and remove from history where possible.

## Change Control (Enterprise)
- Prefer minimal diffs, idempotent patches, and deterministic behavior.
- Before edits: show context (relevant file excerpt or `git diff` plan).
- After edits: run syntax checks/tests relevant to the change.
- Never restart services unless required; if required: controlled restart + smoke test.

## Coding Standards
- Python: type hints, clear error handling, no hidden side-effects.
- SQL: parameterized queries, stable schemas, defensive defaults.
- Templates: insert markers for idempotent UI patches (e.g., `MBR_DOWNLOAD_BUTTON`).

## Verification Checklist (when touching app)
- `python -m py_compile` for changed modules.
- App route smoke test via `curl` (expected status codes).
- If service restart occurred: `systemctl status invoice-app` and re-check endpoints.

## MBR Feature Contract
- `/mbr/monthly.pptx` must remain auth-guarded (`require_login`), return editable PPTX.
- Deterministic fallback must work without LLM (`MBR_USE_LLM=0`).
- Template placeholders must remain stable:
  - `{{TOP_SUPPLIERS_TABLE}}`, `{{BUDGET_CHART}}`, `{{TOTAL_NET}}`, etc.
