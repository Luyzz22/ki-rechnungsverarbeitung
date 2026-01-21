# SBS Deutschland - Enterprise Agent Instructions

> **Version:** 2.0.0  
> **Last Updated:** 2026-01-21  
> **Classification:** Internal - Engineering

---

## 1. System Overview

### Infrastructure
| Component | Value | Notes |
|-----------|-------|-------|
| **Server** | 207.154.200.239 | Ubuntu 24.04 LTS |
| **Workspace** | `/var/www/invoice-app` | Git-controlled |
| **Service** | `invoice-app.service` | systemd managed |
| **Runtime** | Uvicorn/FastAPI | Port 8000 (internal) |
| **Database** | SQLite | `/var/www/invoice-app/invoices.db` |
| **Domain** | app.sbsdeutschland.com | HTTPS via Nginx |

### Application Stack
```
┌─────────────────────────────────────────────────────────┐
│                    Nginx (HTTPS/443)                    │
├─────────────────────────────────────────────────────────┤
│                 FastAPI/Uvicorn (:8000)                 │
├──────────────┬──────────────┬──────────────┬────────────┤
│   Auth/SSO   │     RBAC     │   MBR Gen    │  Invoice   │
│   (OAuth)    │   (Roles)    │   (AI/LLM)   │  Process   │
├──────────────┴──────────────┴──────────────┴────────────┤
│                    SQLite Database                      │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Security & Compliance

### 2.1 Workspace Scope (STRICT)
- ✅ **Allowed:** `/var/www/invoice-app` and subdirectories
- ❌ **Forbidden:** `/etc`, `/var/log`, `/home/*`, `/root`, backups outside repo
- ❌ **Never:** Access other users' data, cross-tenant queries

### 2.2 Secrets Management
| Rule | Enforcement |
|------|-------------|
| Never print/log secrets | Runtime checks |
| Never commit to Git | Pre-commit hooks |
| Store in `/etc/default/invoice-app` | Environment injection |
| Rotate on exposure | Immediate action required |

**Protected Secrets:**
- `OPENAI_API_KEY` / `MBR_LLM_API_KEY`
- `GOOGLE_CLIENT_SECRET`
- `MICROSOFT_CLIENT_SECRET`
- `SENDGRID_API_KEY`
- Database credentials (future)

### 2.3 Data Privacy (GDPR/Enterprise)
- All queries MUST filter by `user_id` where applicable
- User data isolation is MANDATORY across:
  - Invoices (`rechnungen.user_id`)
  - Documents
  - Reports (MBR)
  - Analytics
- Audit trail for data access (planned)

---

## 3. Authentication & Authorization

### 3.1 Authentication Methods
| Method | Status | Use Case |
|--------|--------|----------|
| Email/Password | ✅ Active | Default login |
| Google OAuth | ✅ Active | SSO for Google Workspace |
| Microsoft Entra ID | 🔄 Pending | SSO for Enterprise |
| SAML 2.0 | 📋 Planned | Generic Enterprise IdP |

**OAuth Callback URLs:**
```
https://app.sbsdeutschland.com/auth/google/callback
https://app.sbsdeutschland.com/auth/microsoft/callback
```

### 3.2 Role-Based Access Control (RBAC)
| Role | Permissions | Scope |
|------|-------------|-------|
| `owner` | Full access, billing, delete org | Organization |
| `admin` | User management, settings | Organization |
| `manager` | Approve invoices, view reports | Team |
| `member` | Upload, view own data | Personal |
| `viewer` | Read-only access | Assigned data |

**Permission Matrix:**
```
Action              │ owner │ admin │ manager │ member │ viewer
────────────────────┼───────┼───────┼─────────┼────────┼────────
Upload invoices     │   ✓   │   ✓   │    ✓    │   ✓    │   ✗
View own invoices   │   ✓   │   ✓   │    ✓    │   ✓    │   ✓
View team invoices  │   ✓   │   ✓   │    ✓    │   ✗    │   ✗
Approve invoices    │   ✓   │   ✓   │    ✓    │   ✗    │   ✗
Download MBR        │   ✓   │   ✓   │    ✓    │   ✓    │   ✗
Manage users        │   ✓   │   ✓   │    ✗    │   ✗    │   ✗
Billing/Plans       │   ✓   │   ✗   │    ✗    │   ✗    │   ✗
Delete organization │   ✓   │   ✗   │    ✗    │   ✗    │   ✗
```

---

## 4. Feature Contracts

### 4.1 MBR (Monthly Business Review)

**Endpoint:** `GET /mbr/monthly.pptx`

| Aspect | Requirement |
|--------|-------------|
| Auth | `require_login` - Session-based |
| User Isolation | Filter by `user_id` (MANDATORY) |
| Output | Editable PPTX (7 slides) |
| LLM Fallback | `MBR_USE_LLM=0` must work |

**Template Placeholders (STABLE - DO NOT CHANGE):**
```
{{MBR_MONTH}}              - Month label (e.g., "Januar 2026")
{{COVERAGE_NOTE}}          - Data source note
{{INVOICE_COUNT}}          - Number of invoices
{{TOTAL_NET}}              - Net total (formatted)
{{TOTAL_GROSS}}            - Gross total (formatted)
{{TOP_SUPPLIERS_TABLE}}    - Rendered as table
{{BUDGET_CHART}}           - Rendered as editable chart
{{EXEC_SUMMARY_BULLETS}}   - AI-generated bullets
{{KPI_COMMENTARY_BULLETS}} - AI-generated bullets
{{SUPPLIER_INSIGHTS_BULLETS}} - AI-generated bullets
{{BUDGET_INSIGHTS_BULLETS}}   - AI-generated bullets
{{CLOSING_STATEMENT}}      - AI-generated summary
```

**Slide Structure (v2.0):**
1. Title Slide (SBS Branding)
2. Executive Summary + KPIs
3. Top Lieferanten (Table + Insights)
4. Budget-Analyse (Chart + Insights)
5. KPI-Kommentar
6. Risiken & Maßnahmen
7. Closing Statement

### 4.2 Invoice Processing

**Endpoint:** `POST /api/upload`

| Aspect | Requirement |
|--------|-------------|
| Auth | Required |
| User Isolation | Set `user_id` on creation |
| File Types | PDF, PNG, JPG |
| Processing | AI extraction → Review → Approve |

### 4.3 SSO/OAuth

**Endpoints:**
- `GET /auth/google` - Initiate Google OAuth
- `GET /auth/google/callback` - Google callback
- `GET /auth/microsoft` - Initiate Microsoft OAuth
- `GET /auth/microsoft/callback` - Microsoft callback
- `GET /auth/sso/status` - Check configured providers

---

## 5. Database Schema (Critical Tables)

### Users
```sql
users (
  id, email, password_hash, name, company,
  oauth_provider, oauth_id, oauth_email,  -- SSO
  current_org_id, is_admin,               -- RBAC
  created_at, last_login, is_active
)
```

### Invoices
```sql
rechnungen (
  id, rechnungs_nummer, lieferant,
  rechnungs_datum, faelligkeits_datum,
  netto_betrag, brutto_betrag, wahrung,
  status, kategorie_id, datei_pfad,
  user_id,  -- USER ISOLATION (CRITICAL)
  erstellt_am
)
```

### Organizations (RBAC)
```sql
organizations (id, name, owner_id, plan, created_at)
org_members (id, org_id, user_id, role, invited_by, created_at)
```

---

## 6. Change Control (Enterprise)

### 6.1 Pre-Change Checklist
- [ ] Identify affected files
- [ ] Show context (relevant excerpts)
- [ ] Plan minimal diff
- [ ] Verify no secrets exposed

### 6.2 Post-Change Checklist
- [ ] `python -m py_compile <changed_files>`
- [ ] Run relevant smoke tests
- [ ] If service restart: `systemctl restart invoice-app`
- [ ] Verify: `systemctl status invoice-app`
- [ ] Smoke test endpoints via `curl`

### 6.3 Smoke Test Commands
```bash
# Health check
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/

# MBR auth guard (expect 303)
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/mbr/monthly.pptx

# SSO status
curl -s http://127.0.0.1:8000/auth/sso/status
```

---

## 7. Coding Standards

### Python
- Type hints required
- Clear error handling with logging
- No hidden side-effects
- Docstrings for public functions

### SQL
- Parameterized queries ONLY (no string interpolation)
- Always include `user_id` filter where applicable
- Defensive defaults (COALESCE, NULLIF)

### Templates
- Use markers for idempotent patches
- Example: `<!-- MBR_DOWNLOAD_BUTTON: do not remove -->`
- Consistent SBS branding (#003856, #FFB900)

---

## 8. Monitoring & Operations

### 8.1 Log Locations
```
/var/log/nginx/access.log     - HTTP requests
/var/log/nginx/error.log      - Nginx errors
journalctl -u invoice-app     - Application logs
```

### 8.2 Health Checks
| Endpoint | Expected | Frequency |
|----------|----------|-----------|
| `GET /` | 200 | 1 min |
| `GET /api/health` | 200 | 1 min |
| DB connectivity | OK | 5 min |

### 8.3 Alerting (Planned)
- 5xx error rate > 1%
- Response time p95 > 2s
- Disk usage > 80%
- SSL certificate expiry < 14 days

---

## 9. Backup & Recovery

### 9.1 Database Backup
```bash
# Manual backup
sqlite3 /var/www/invoice-app/invoices.db ".backup '/backup/invoices_$(date +%Y%m%d).db'"

# Automated (cron) - planned
0 2 * * * /var/www/invoice-app/scripts/backup_db.sh
```

### 9.2 Recovery Procedure
1. Stop service: `systemctl stop invoice-app`
2. Restore DB: `cp /backup/invoices_YYYYMMDD.db /var/www/invoice-app/invoices.db`
3. Verify integrity: `sqlite3 invoices.db "PRAGMA integrity_check;"`
4. Start service: `systemctl start invoice-app`
5. Smoke test all endpoints

---

## 10. Roadmap Status

| Feature | Status | Notes |
|---------|--------|-------|
| ✅ Audit Trail | DONE | Logging implemented |
| ✅ RBAC | DONE | Roles & permissions |
| ✅ Google SSO | DONE | OAuth 2.0 |
| 🔄 Microsoft SSO | PENDING | Azure account needed |
| ✅ MBR Enterprise | DONE | 7 slides, AI insights |
| 📋 API Rate Limiting | PLANNED | Next priority |
| 📋 API Documentation | PLANNED | OpenAPI/Swagger |
| 📋 PostgreSQL Migration | PLANNED | Scalability |

---

## 11. Contact & Escalation

| Role | Contact | Scope |
|------|---------|-------|
| Engineering Lead | Luis Schenk | Technical decisions |
| Infrastructure | Luis Schenk | Server, deployment |
| Security | Luis Schenk | Auth, data privacy |

---

*This document is the source of truth for AI agents and developers working on SBS invoice-app.*
