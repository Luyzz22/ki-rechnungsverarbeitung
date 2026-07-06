"""Server-side tenant processing policy resolution for FlowCheck+."""
from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from shared.inference_policy import InferenceProfile, InferenceProvider
from shared.providers.azure_identity import get_bool_config_value, get_config_value, is_production_runtime


class CloudProcessingRegion(str, Enum):
    UNSET = "unset"
    EU = "eu"
    LOCAL_ONLY = "local_only"


TENANT_POLICY_ERROR_CODE = "TENANT_PROCESSING_POLICY_DENIED"
LOCAL_PROVIDER_ERROR_CODE = "SOVEREIGN_INFERENCE_UNAVAILABLE"
SERVER_POLICY_SOURCE = "server_config"
DATABASE_POLICY_SOURCE = "database"
DEFAULT_POLICY_SOURCE = "default"
CLIENT_POLICY_SOURCES = frozenset({"client", "client_input", "http", "request", "query", "header", "cookie", "body"})
LOCAL_PROVIDERS = frozenset({InferenceProvider.LOCAL_OPENAI_COMPAT, InferenceProvider.LOCAL_OCR})
EXTERNAL_CLOUD_PROVIDERS = frozenset(
    {
        InferenceProvider.OPENAI_DIRECT,
        InferenceProvider.ANTHROPIC_DIRECT,
        InferenceProvider.GEMINI_DIRECT,
        InferenceProvider.AZURE_OPENAI_EU,
        InferenceProvider.AZURE_DOCUMENT_INTELLIGENCE_EU,
    }
)


class TenantProcessingPolicyError(RuntimeError):
    """PII-free tenant processing policy failure."""

    def __init__(
        self,
        reason_code: str,
        *,
        error_code: str = TENANT_POLICY_ERROR_CODE,
        policy_source: str = "",
    ) -> None:
        self.error_code = error_code
        self.reason_code = reason_code
        self.policy_source = policy_source
        super().__init__(f"{error_code}: {reason_code}")

    def to_safe_dict(self) -> dict[str, str]:
        return {
            "error_code": self.error_code,
            "reason_code": self.reason_code,
            "policy_source": self.policy_source,
        }


@dataclass(frozen=True)
class TenantProcessingPolicyDecision:
    cloud_processing_region: CloudProcessingRegion
    effective_inference_profile: InferenceProfile
    policy_source: str
    is_external_cloud_allowed: bool
    organization_id: int | None = None
    reason_code: str = "allowed"


PermissionChecker = Callable[[int, int, str], bool]


def ensure_organization_processing_policy_schema(connection: sqlite3.Connection) -> None:
    """Create/migrate the legacy organization tables for processing policy use."""
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT UNIQUE,
            plan TEXT DEFAULT 'free',
            cloud_processing_region TEXT DEFAULT 'unset',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS org_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            invited_by INTEGER,
            joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(org_id, user_id)
        )
        """
    )
    _ensure_column(cursor, "organizations", "cloud_processing_region", "TEXT DEFAULT 'unset'")
    _ensure_column(cursor, "organizations", "slug", "TEXT")
    _ensure_column(cursor, "organizations", "plan", "TEXT DEFAULT 'free'")
    _ensure_column(cursor, "org_members", "invited_by", "INTEGER")
    _ensure_column(cursor, "org_members", "joined_at", "TEXT DEFAULT CURRENT_TIMESTAMP")
    _ensure_column(cursor, "org_members", "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP")
    connection.commit()


def resolve_tenant_processing_policy(
    *,
    organization_id: int | None = None,
    cloud_processing_region: CloudProcessingRegion | str | None = None,
    connection: sqlite3.Connection | None = None,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
    policy_source: str | None = None,
) -> TenantProcessingPolicyDecision:
    """Resolve the effective processing policy from trusted server-side state."""
    source = (policy_source or SERVER_POLICY_SOURCE).strip().lower()
    if source in CLIENT_POLICY_SOURCES:
        raise TenantProcessingPolicyError("client_processing_policy_override_denied", policy_source=source)

    if cloud_processing_region is not None:
        region = parse_cloud_processing_region(cloud_processing_region, policy_source=source)
        resolved_source = source or SERVER_POLICY_SOURCE
    elif organization_id is not None and connection is not None:
        region = _load_organization_region(connection, organization_id)
        resolved_source = DATABASE_POLICY_SOURCE
    else:
        region = CloudProcessingRegion.UNSET
        resolved_source = DEFAULT_POLICY_SOURCE

    if region == CloudProcessingRegion.EU:
        return TenantProcessingPolicyDecision(
            cloud_processing_region=region,
            effective_inference_profile=InferenceProfile.EU_REGIONAL_CLOUD,
            policy_source=resolved_source,
            is_external_cloud_allowed=True,
            organization_id=organization_id,
        )
    if region == CloudProcessingRegion.LOCAL_ONLY:
        return TenantProcessingPolicyDecision(
            cloud_processing_region=region,
            effective_inference_profile=InferenceProfile.SOVEREIGN,
            policy_source=resolved_source,
            is_external_cloud_allowed=False,
            organization_id=organization_id,
        )

    profile = _resolve_default_profile(settings=settings, env=env, policy_source=resolved_source)
    external_allowed = not (
        is_production_runtime(settings=settings, env=env)
        and _eu_regional_cloud_required(settings=settings, env=env)
    )
    reason_code = "production_requires_tenant_processing_region" if not external_allowed else "allowed"
    return TenantProcessingPolicyDecision(
        cloud_processing_region=CloudProcessingRegion.UNSET,
        effective_inference_profile=profile,
        policy_source=resolved_source,
        is_external_cloud_allowed=external_allowed,
        organization_id=organization_id,
        reason_code=reason_code,
    )


def assert_tenant_provider_allowed(
    decision: TenantProcessingPolicyDecision,
    *,
    provider: InferenceProvider | str,
    local_provider_available: bool = False,
) -> TenantProcessingPolicyDecision:
    """Fail closed when tenant policy forbids the selected provider class."""
    provider_enum = provider if isinstance(provider, InferenceProvider) else InferenceProvider(str(provider))
    if decision.cloud_processing_region == CloudProcessingRegion.LOCAL_ONLY:
        if provider_enum not in LOCAL_PROVIDERS:
            raise TenantProcessingPolicyError("local_only_provider_required", policy_source=decision.policy_source)
        if not local_provider_available:
            raise TenantProcessingPolicyError(
                "local_provider_unavailable",
                error_code=LOCAL_PROVIDER_ERROR_CODE,
                policy_source=decision.policy_source,
            )
    if not decision.is_external_cloud_allowed and provider_enum in EXTERNAL_CLOUD_PROVIDERS:
        raise TenantProcessingPolicyError("external_cloud_not_allowed", policy_source=decision.policy_source)
    if decision.cloud_processing_region == CloudProcessingRegion.EU and provider_enum in {
        InferenceProvider.OPENAI_DIRECT,
        InferenceProvider.ANTHROPIC_DIRECT,
        InferenceProvider.GEMINI_DIRECT,
    }:
        raise TenantProcessingPolicyError("direct_provider_not_allowed", policy_source=decision.policy_source)
    return decision


def set_organization_cloud_processing_region(
    *,
    organization_id: int,
    cloud_processing_region: CloudProcessingRegion | str,
    actor_user_id: int,
    connection: sqlite3.Connection | None = None,
    permission_checker: PermissionChecker | None = None,
) -> CloudProcessingRegion:
    """Set an organization's processing region through the server-side service layer."""
    region = parse_cloud_processing_region(cloud_processing_region, policy_source=SERVER_POLICY_SOURCE)
    owns_connection = connection is None
    if connection is None:
        from database import get_connection

        connection = get_connection()

    if permission_checker is None and not owns_connection:
        has_permission = _check_organization_permission(connection, actor_user_id, organization_id, "admin")
    elif permission_checker is None:
        from organizations import OrgRole, check_permission

        permission_checker = check_permission
        has_permission = permission_checker(actor_user_id, organization_id, OrgRole.ADMIN)
    else:
        has_permission = permission_checker(actor_user_id, organization_id, "admin")

    if not has_permission:
        raise TenantProcessingPolicyError("organization_admin_required", policy_source=SERVER_POLICY_SOURCE)

    try:
        ensure_organization_processing_policy_schema(connection)
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE organizations SET cloud_processing_region = ? WHERE id = ?",
            (region.value, organization_id),
        )
        if cursor.rowcount == 0:
            raise TenantProcessingPolicyError("organization_not_found", policy_source=SERVER_POLICY_SOURCE)
        connection.commit()
        return region
    finally:
        if owns_connection:
            connection.close()


def parse_cloud_processing_region(
    value: CloudProcessingRegion | str,
    *,
    policy_source: str = SERVER_POLICY_SOURCE,
) -> CloudProcessingRegion:
    if isinstance(value, CloudProcessingRegion):
        return value
    normalized = str(value or "").strip().lower()
    if normalized in {"unset", "UNSET".lower()}:
        return CloudProcessingRegion.UNSET
    if normalized == "eu":
        return CloudProcessingRegion.EU
    if normalized in {"local_only", "local-only", "localonly"}:
        return CloudProcessingRegion.LOCAL_ONLY
    raise TenantProcessingPolicyError("cloud_processing_region_invalid", policy_source=policy_source)


def _load_organization_region(connection: sqlite3.Connection, organization_id: int) -> CloudProcessingRegion:
    ensure_organization_processing_policy_schema(connection)
    cursor = connection.cursor()
    cursor.execute("SELECT cloud_processing_region FROM organizations WHERE id = ?", (organization_id,))
    row = cursor.fetchone()
    if not row:
        raise TenantProcessingPolicyError("organization_not_found", policy_source=DATABASE_POLICY_SOURCE)
    value = row[0] if not isinstance(row, sqlite3.Row) else row["cloud_processing_region"]
    return parse_cloud_processing_region(value or CloudProcessingRegion.UNSET.value, policy_source=DATABASE_POLICY_SOURCE)


def _resolve_default_profile(
    *,
    settings: Any | None,
    env: Mapping[str, str] | None,
    policy_source: str,
) -> InferenceProfile:
    value = get_config_value(
        "FLOWCHECK_DEFAULT_INFERENCE_PROFILE",
        settings=settings,
        env=env,
        default=InferenceProfile.STANDARD.value,
    ).strip() or InferenceProfile.STANDARD.value
    try:
        profile = InferenceProfile(value)
    except ValueError:
        raise TenantProcessingPolicyError("default_inference_profile_invalid", policy_source=policy_source) from None
    if profile == InferenceProfile.PROFESSIONAL_SECRECY:
        raise TenantProcessingPolicyError("professional_secrecy_not_tenant_selectable", policy_source=policy_source)
    return profile


def _eu_regional_cloud_required(*, settings: Any | None, env: Mapping[str, str] | None) -> bool:
    return get_bool_config_value(
        "FLOWCHECK_REQUIRE_EU_REGIONAL_CLOUD_IN_PRODUCTION",
        settings=settings,
        env=env,
        default=False,
    )


def _check_organization_permission(
    connection: sqlite3.Connection,
    actor_user_id: int,
    organization_id: int,
    required_role: str,
) -> bool:
    role_hierarchy = {
        "viewer": 0,
        "member": 1,
        "admin": 2,
        "owner": 3,
    }
    cursor = connection.cursor()
    cursor.execute(
        "SELECT role FROM org_members WHERE org_id = ? AND user_id = ?",
        (organization_id, actor_user_id),
    )
    row = cursor.fetchone()
    if not row:
        return False
    role = row[0] if not isinstance(row, sqlite3.Row) else row["role"]
    return role_hierarchy.get(str(role), 0) >= role_hierarchy.get(required_role, 0)


def _ensure_column(cursor: sqlite3.Cursor, table: str, column: str, definition: str) -> None:
    cursor.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cursor.fetchall()}
    if column not in existing:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
