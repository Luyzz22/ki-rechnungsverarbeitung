"""Trusted organization context resolution for inference-bearing flows."""
from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from shared.inference_policy import DataClass, InferenceProfile, InferenceProvider
from shared.providers.azure_identity import get_bool_config_value, is_production_runtime
from shared.tenant_processing_policy import (
    TenantProcessingPolicyDecision,
    assert_tenant_provider_allowed,
    resolve_tenant_processing_policy,
)


ORG_CONTEXT_ERROR_CODE = "ORG_CONTEXT_REQUIRED"
CLIENT_CONTEXT_KEYS = frozenset(
    {
        "organization_id",
        "org_id",
        "tenant_id",
        "cloud_processing_region",
        "effective_inference_profile",
        "inference_profile",
        "provider_allowlist",
        "provider_governance_approved",
        "retention_evidence_ref",
        "no_training_evidence_ref",
    }
)


class OrganizationContextError(RuntimeError):
    """PII-free trusted organization context failure."""

    def __init__(self, reason_code: str, *, error_code: str = ORG_CONTEXT_ERROR_CODE) -> None:
        self.error_code = error_code
        self.reason_code = reason_code
        super().__init__(f"{error_code}: {reason_code}")

    def to_safe_dict(self) -> dict[str, str]:
        return {"error_code": self.error_code, "reason_code": self.reason_code}


@dataclass(frozen=True)
class TrustedOrganizationContext:
    organization_id: int | str | None
    user_id: int | str | None
    source: str
    tenant_id: str | None = None
    demo_flow: bool = False

    def to_safe_dict(self) -> dict[str, str | bool]:
        return {
            "source": self.source,
            "has_organization": self.organization_id is not None,
            "demo_flow": self.demo_flow,
        }


def resolve_trusted_organization_context(
    *,
    session: Mapping[str, Any] | None = None,
    authenticated_user_id: int | str | None = None,
    authenticated_tenant_id: str | None = None,
    invoice_id: int | str | None = None,
    job_id: str | None = None,
    trusted_organization_id: int | str | None = None,
    client_input: Mapping[str, Any] | None = None,
    connection: sqlite3.Connection | None = None,
    allow_demo_exception: bool = False,
    demo_flow: bool = False,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
) -> TrustedOrganizationContext | None:
    """Resolve organization context only from trusted server-side sources."""
    _reject_client_context_override(client_input)

    if authenticated_tenant_id:
        return TrustedOrganizationContext(
            organization_id=str(authenticated_tenant_id),
            tenant_id=str(authenticated_tenant_id),
            user_id=authenticated_user_id,
            source="authenticated_tenant",
        )

    session_user_id = _session_user_id(session)
    user_id = authenticated_user_id if authenticated_user_id is not None else session_user_id

    owns_connection = connection is None
    if connection is None and any(value is not None for value in (user_id, invoice_id, job_id, trusted_organization_id)):
        from database import get_connection

        connection = get_connection()

    try:
        if invoice_id is not None and connection is not None:
            return _resolve_from_invoice(connection, invoice_id, user_id)
        if job_id is not None and connection is not None:
            return _resolve_from_job(connection, job_id, user_id)
        if trusted_organization_id is not None and connection is not None:
            return _resolve_from_trusted_org_id(connection, trusted_organization_id, user_id)
        if user_id is not None and connection is not None:
            context = _resolve_from_user(connection, user_id)
            if context is not None:
                return context
    finally:
        if owns_connection and connection is not None:
            connection.close()

    if allow_demo_exception and demo_flow and _is_development_or_test(settings=settings, env=env):
        return TrustedOrganizationContext(
            organization_id=None,
            user_id=user_id,
            source="explicit_demo_exception",
            demo_flow=True,
        )

    return None


def require_trusted_organization_context(
    *,
    context: TrustedOrganizationContext | None = None,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
    allow_demo_exception: bool = False,
) -> TrustedOrganizationContext:
    if context is not None:
        return context
    if allow_demo_exception and _is_development_or_test(settings=settings, env=env):
        return TrustedOrganizationContext(
            organization_id=None,
            user_id=None,
            source="explicit_demo_exception",
            demo_flow=True,
        )
    if _requires_context(settings=settings, env=env):
        raise OrganizationContextError("organization_context_missing")
    raise OrganizationContextError("organization_context_missing")


def assert_organization_inference_allowed(
    *,
    organization_context: TrustedOrganizationContext | None,
    data_class: DataClass | str,
    requested_inference_profile: InferenceProfile | str | None,
    provider: InferenceProvider | str,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
    connection: sqlite3.Connection | None = None,
    local_provider_available: bool = False,
    allow_demo_exception: bool = False,
) -> InferenceProfile:
    """Resolve the effective profile and enforce tenant provider restrictions."""
    data_class_enum = data_class if isinstance(data_class, DataClass) else DataClass(str(data_class))
    if organization_context is None:
        if _requires_context(settings=settings, env=env):
            raise OrganizationContextError("organization_context_missing")
        if data_class_enum == DataClass.DEMO and allow_demo_exception:
            return _coerce_profile(requested_inference_profile)
        return _coerce_profile(requested_inference_profile)

    if organization_context.demo_flow:
        if data_class_enum != DataClass.DEMO:
            raise OrganizationContextError("demo_context_requires_demo_data")
        return _coerce_profile(requested_inference_profile)

    decision = resolve_tenant_policy_for_context(
        organization_context,
        settings=settings,
        env=env,
        connection=connection,
    )
    assert_tenant_provider_allowed(
        decision,
        provider=provider,
        local_provider_available=local_provider_available,
    )
    return decision.effective_inference_profile


def resolve_tenant_policy_for_context(
    organization_context: TrustedOrganizationContext,
    *,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
    connection: sqlite3.Connection | None = None,
) -> TenantProcessingPolicyDecision:
    """Resolve tenant policy from trusted context without accepting client fields."""
    if organization_context.demo_flow:
        return resolve_tenant_processing_policy(settings=settings, env=env)

    org_id = organization_context.organization_id
    if isinstance(org_id, int) or (isinstance(org_id, str) and org_id.isdigit()):
        owns_connection = connection is None
        if connection is None:
            from database import get_connection

            connection = get_connection()
        try:
            return resolve_tenant_processing_policy(
                organization_id=int(org_id),
                connection=connection,
                settings=settings,
                env=env,
            )
        finally:
            if owns_connection:
                connection.close()

    return resolve_tenant_processing_policy(settings=settings, env=env)


def _reject_client_context_override(client_input: Mapping[str, Any] | None) -> None:
    if not client_input:
        return
    if any(key in client_input for key in CLIENT_CONTEXT_KEYS):
        raise OrganizationContextError("client_context_override_denied")


def _session_user_id(session: Mapping[str, Any] | None) -> int | str | None:
    if not session:
        return None
    return session.get("user_id")


def _resolve_from_user(connection: sqlite3.Connection, user_id: int | str) -> TrustedOrganizationContext | None:
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT current_org_id FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        current_org_id = _row_value(row, "current_org_id", 0) if row else None
    except sqlite3.Error:
        current_org_id = None
    if current_org_id and _is_member(connection, user_id, current_org_id):
        return TrustedOrganizationContext(organization_id=current_org_id, user_id=user_id, source="user_current_org")

    try:
        cursor.execute(
            "SELECT org_id FROM org_members WHERE user_id = ? ORDER BY CASE role WHEN 'owner' THEN 0 WHEN 'admin' THEN 1 ELSE 2 END, org_id LIMIT 1",
            (user_id,),
        )
        member_row = cursor.fetchone()
    except sqlite3.Error:
        member_row = None
    if member_row:
        return TrustedOrganizationContext(organization_id=_row_value(member_row, "org_id", 0), user_id=user_id, source="org_membership")
    return None


def _resolve_from_trusted_org_id(
    connection: sqlite3.Connection,
    organization_id: int | str,
    user_id: int | str | None,
) -> TrustedOrganizationContext:
    if user_id is not None and not _is_member(connection, user_id, organization_id):
        raise OrganizationContextError("organization_membership_required")
    return TrustedOrganizationContext(organization_id=organization_id, user_id=user_id, source="trusted_server_org")


def _resolve_from_job(
    connection: sqlite3.Connection,
    job_id: str,
    user_id: int | str | None,
) -> TrustedOrganizationContext:
    cursor = connection.cursor()
    cursor.execute("SELECT user_id FROM jobs WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    if not row:
        raise OrganizationContextError("organization_context_missing")
    owner_user_id = _row_value(row, "user_id", 0)
    owner_context = _resolve_from_user(connection, owner_user_id)
    if owner_context is None:
        raise OrganizationContextError("organization_context_missing")
    if user_id is not None and not _is_member(connection, user_id, owner_context.organization_id):
        raise OrganizationContextError("organization_membership_required")
    return TrustedOrganizationContext(organization_id=owner_context.organization_id, user_id=user_id or owner_user_id, source="job_owner")


def _resolve_from_invoice(
    connection: sqlite3.Connection,
    invoice_id: int | str,
    user_id: int | str | None,
) -> TrustedOrganizationContext:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT j.user_id
        FROM invoices i
        JOIN jobs j ON i.job_id = j.job_id
        WHERE i.id = ?
        """,
        (invoice_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise OrganizationContextError("organization_context_missing")
    owner_user_id = _row_value(row, "user_id", 0)
    owner_context = _resolve_from_user(connection, owner_user_id)
    if owner_context is None:
        raise OrganizationContextError("organization_context_missing")
    if user_id is not None and not _is_member(connection, user_id, owner_context.organization_id):
        raise OrganizationContextError("organization_membership_required")
    return TrustedOrganizationContext(organization_id=owner_context.organization_id, user_id=user_id or owner_user_id, source="invoice_owner")


def _is_member(connection: sqlite3.Connection, user_id: int | str, organization_id: int | str | None) -> bool:
    if organization_id is None:
        return False
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT 1 FROM org_members WHERE user_id = ? AND org_id = ?",
            (user_id, organization_id),
        )
        return cursor.fetchone() is not None
    except sqlite3.Error:
        return False


def _row_value(row: Any, key: str, index: int) -> Any:
    if isinstance(row, sqlite3.Row):
        return row[key]
    return row[index]


def _coerce_profile(value: InferenceProfile | str | None) -> InferenceProfile:
    if isinstance(value, InferenceProfile):
        return value
    if value:
        return InferenceProfile(str(value))
    return InferenceProfile.STANDARD


def _requires_context(*, settings: Any | None, env: Mapping[str, str] | None) -> bool:
    return is_production_runtime(settings=settings, env=env) or get_bool_config_value(
        "FLOWCHECK_REQUIRE_EU_REGIONAL_CLOUD_IN_PRODUCTION",
        settings=settings,
        env=env,
        default=False,
    )


def _is_development_or_test(*, settings: Any | None, env: Mapping[str, str] | None) -> bool:
    if is_production_runtime(settings=settings, env=env):
        return False
    value = ""
    if env is not None:
        value = (env.get("FLOWCHECK_RUNTIME_ENV") or env.get("APP_ENV") or env.get("ENVIRONMENT") or "").strip().lower()
    elif settings is not None:
        value = str(getattr(settings, "flowcheck_runtime_env", "") or getattr(settings, "app_env", "")).strip().lower()
    return value in {"", "development", "dev", "test", "ci"}
