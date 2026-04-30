from __future__ import annotations

import contextvars
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_tenant_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("tenant_id", default=None)


@dataclass
class TenantContext:
    tenant_id: str

    @staticmethod
    def set_current_tenant(tenant_id: str) -> None:
        if not tenant_id:
            raise ValueError("tenant_id must not be empty")
        _tenant_id_ctx.set(tenant_id)

    @staticmethod
    def get_current_tenant() -> str:
        tenant_id = _tenant_id_ctx.get()
        if tenant_id:
            return tenant_id
        # Tenant context missing. Tracked as F-10 in
        # docs/FLOWCHECK_SECURITY_HOTFIX_PLAN.md: silently returning
        # "default-tenant" in production breaks tenant isolation. Fail-closed
        # outside of dev/test/ci so missing X-Tenant-ID headers or background
        # jobs that forgot to set the tenant cannot leak data across tenants.
        env = (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "").strip().lower()
        if env in ("development", "dev", "test", "ci"):
            logger.warning(
                "TenantContext: get_current_tenant() called without an active "
                "tenant; returning 'default-tenant' insecure fallback (env=%s). "
                "This MUST NOT happen in production.",
                env,
            )
            return "default-tenant"
        raise RuntimeError(
            "TenantContext: get_current_tenant() called without an active "
            "tenant. Ensure the request supplied an X-Tenant-ID header or that "
            "the background task called TenantContext.set_current_tenant(...) "
            "before invoking tenant-scoped logic. Refusing to fall back to "
            "'default-tenant' to preserve tenant isolation."
        )
