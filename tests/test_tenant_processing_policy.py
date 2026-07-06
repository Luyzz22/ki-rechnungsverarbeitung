import sqlite3

import pytest

import database
from shared.inference_policy import DataClass, InferenceProfile, InferenceProvider
from shared.providers.provider_factory import select_provider_for_purpose
from shared.tenant_processing_policy import (
    CloudProcessingRegion,
    TenantProcessingPolicyError,
    assert_tenant_provider_allowed,
    ensure_organization_processing_policy_schema,
    resolve_tenant_processing_policy,
    set_organization_cloud_processing_region,
)


def _prod_env(**overrides):
    env = {
        "FLOWCHECK_RUNTIME_ENV": "production",
        "FLOWCHECK_REQUIRE_EU_REGIONAL_CLOUD_IN_PRODUCTION": "true",
        "FLOWCHECK_DEFAULT_INFERENCE_PROFILE": "standard",
    }
    env.update(overrides)
    return env


@pytest.fixture
def org_db(tmp_path, monkeypatch):
    db_path = tmp_path / "tenant_policy.db"
    monkeypatch.setattr(database, "_ensure_db_path", lambda: db_path)
    database.init_database()
    database.init_users_table()
    conn = database.get_connection()
    yield conn
    conn.close()


def _create_org_with_members(conn: sqlite3.Connection) -> int:
    conn.execute("INSERT INTO users (id, email, password_hash, name) VALUES (?, ?, ?, ?)", (1, "owner@example.test", "hash", "Owner"))
    conn.execute("INSERT INTO users (id, email, password_hash, name) VALUES (?, ?, ?, ?)", (2, "admin@example.test", "hash", "Admin"))
    conn.execute("INSERT INTO users (id, email, password_hash, name) VALUES (?, ?, ?, ?)", (3, "member@example.test", "hash", "Member"))
    conn.execute("INSERT INTO organizations (id, name, slug, plan) VALUES (?, ?, ?, ?)", (10, "Example Org", "example-org", "free"))
    conn.execute("INSERT INTO org_members (org_id, user_id, role) VALUES (?, ?, ?)", (10, 1, "owner"))
    conn.execute("INSERT INTO org_members (org_id, user_id, role) VALUES (?, ?, ?)", (10, 2, "admin"))
    conn.execute("INSERT INTO org_members (org_id, user_id, role) VALUES (?, ?, ?)", (10, 3, "member"))
    conn.commit()
    return 10


def test_fresh_sqlite_organization_defaults_to_unset(org_db):
    org_id = _create_org_with_members(org_db)

    row = org_db.execute("SELECT cloud_processing_region FROM organizations WHERE id = ?", (org_id,)).fetchone()
    assert row["cloud_processing_region"] == CloudProcessingRegion.UNSET.value

    decision = resolve_tenant_processing_policy(organization_id=org_id, connection=org_db)
    assert decision.cloud_processing_region == CloudProcessingRegion.UNSET
    assert decision.effective_inference_profile == InferenceProfile.STANDARD
    assert decision.policy_source == "database"


def test_old_sqlite_database_without_region_column_is_compatible():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE organizations (id INTEGER PRIMARY KEY, name TEXT, slug TEXT, plan TEXT)")
    conn.execute("CREATE TABLE org_members (id INTEGER PRIMARY KEY, org_id INTEGER, user_id INTEGER, role TEXT)")
    conn.execute("INSERT INTO organizations (id, name, slug, plan) VALUES (?, ?, ?, ?)", (20, "Old Org", "old-org", "free"))
    conn.commit()

    decision = resolve_tenant_processing_policy(organization_id=20, connection=conn)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(organizations)").fetchall()}

    assert "cloud_processing_region" in columns
    assert decision.cloud_processing_region == CloudProcessingRegion.UNSET
    assert decision.effective_inference_profile == InferenceProfile.STANDARD
    conn.close()


def test_unset_production_enforcement_blocks_external_provider():
    decision = resolve_tenant_processing_policy(
        cloud_processing_region=CloudProcessingRegion.UNSET,
        env=_prod_env(),
    )

    assert decision.is_external_cloud_allowed is False
    with pytest.raises(TenantProcessingPolicyError) as exc_info:
        assert_tenant_provider_allowed(decision, provider=InferenceProvider.OPENAI_DIRECT)

    assert exc_info.value.error_code == "TENANT_PROCESSING_POLICY_DENIED"
    assert exc_info.value.reason_code == "external_cloud_not_allowed"


def test_eu_region_maps_to_eu_regional_cloud_and_routes_to_azure():
    decision = resolve_tenant_processing_policy(cloud_processing_region=CloudProcessingRegion.EU, env=_prod_env())

    assert decision.effective_inference_profile == InferenceProfile.EU_REGIONAL_CLOUD
    assert decision.is_external_cloud_allowed is True

    provider = select_provider_for_purpose(
        data_class=DataClass.INVOICE_CONFIDENTIAL,
        inference_profile=InferenceProfile.STANDARD,
        purpose="invoice_llm_extraction",
        tenant_processing_policy=decision,
    )
    assert provider == InferenceProvider.AZURE_OPENAI_EU


def test_local_only_maps_to_sovereign():
    decision = resolve_tenant_processing_policy(cloud_processing_region=CloudProcessingRegion.LOCAL_ONLY, env=_prod_env())

    assert decision.effective_inference_profile == InferenceProfile.SOVEREIGN
    assert decision.is_external_cloud_allowed is False


def test_local_only_without_local_provider_fails_closed():
    decision = resolve_tenant_processing_policy(cloud_processing_region=CloudProcessingRegion.LOCAL_ONLY, env=_prod_env())

    with pytest.raises(TenantProcessingPolicyError) as exc_info:
        assert_tenant_provider_allowed(
            decision,
            provider=InferenceProvider.LOCAL_OPENAI_COMPAT,
            local_provider_available=False,
        )

    assert exc_info.value.error_code == "SOVEREIGN_INFERENCE_UNAVAILABLE"
    assert exc_info.value.reason_code == "local_provider_unavailable"


def test_invalid_cloud_processing_region_blocks():
    with pytest.raises(TenantProcessingPolicyError) as exc_info:
        resolve_tenant_processing_policy(cloud_processing_region="global", env=_prod_env())

    assert exc_info.value.reason_code == "cloud_processing_region_invalid"


def test_non_admin_cannot_set_processing_policy(org_db):
    org_id = _create_org_with_members(org_db)

    with pytest.raises(TenantProcessingPolicyError) as exc_info:
        set_organization_cloud_processing_region(
            organization_id=org_id,
            cloud_processing_region=CloudProcessingRegion.EU,
            actor_user_id=3,
            connection=org_db,
        )

    assert exc_info.value.reason_code == "organization_admin_required"


def test_owner_or_admin_can_set_processing_policy(org_db):
    org_id = _create_org_with_members(org_db)

    region = set_organization_cloud_processing_region(
        organization_id=org_id,
        cloud_processing_region=CloudProcessingRegion.EU,
        actor_user_id=2,
        connection=org_db,
    )
    row = org_db.execute("SELECT cloud_processing_region FROM organizations WHERE id = ?", (org_id,)).fetchone()

    assert region == CloudProcessingRegion.EU
    assert row["cloud_processing_region"] == CloudProcessingRegion.EU.value


def test_client_input_cannot_override_region_or_routing():
    with pytest.raises(TenantProcessingPolicyError) as exc_info:
        resolve_tenant_processing_policy(
            cloud_processing_region=CloudProcessingRegion.EU,
            policy_source="client_input",
            env=_prod_env(),
        )
    assert exc_info.value.reason_code == "client_processing_policy_override_denied"

    with pytest.raises(TypeError):
        select_provider_for_purpose(
            data_class=DataClass.INVOICE_CONFIDENTIAL,
            inference_profile=InferenceProfile.STANDARD,
            purpose="invoice_llm_extraction",
            cloud_processing_region=CloudProcessingRegion.EU.value,
        )


def test_professional_secrecy_cannot_be_activated_through_tenant_policy():
    with pytest.raises(TenantProcessingPolicyError) as exc_info:
        resolve_tenant_processing_policy(
            cloud_processing_region=CloudProcessingRegion.UNSET,
            env=_prod_env(FLOWCHECK_DEFAULT_INFERENCE_PROFILE=InferenceProfile.PROFESSIONAL_SECRECY.value),
        )

    assert exc_info.value.reason_code == "professional_secrecy_not_tenant_selectable"

    with pytest.raises(TenantProcessingPolicyError):
        set_organization_cloud_processing_region(
            organization_id=1,
            cloud_processing_region=InferenceProfile.PROFESSIONAL_SECRECY.value,
            actor_user_id=1,
            permission_checker=lambda *_args: True,
            connection=sqlite3.connect(":memory:"),
        )


def test_unset_tenant_policy_blocks_standard_external_route_in_production():
    decision = resolve_tenant_processing_policy(
        cloud_processing_region=CloudProcessingRegion.UNSET,
        env=_prod_env(),
    )
    with pytest.raises(TenantProcessingPolicyError) as exc_info:
        select_provider_for_purpose(
            data_class=DataClass.INVOICE_CONFIDENTIAL,
            inference_profile=InferenceProfile.STANDARD,
            purpose="invoice_llm_extraction",
            tenant_processing_policy=decision,
            env=_prod_env(),
        )

    assert exc_info.value.reason_code == "external_cloud_not_allowed"
