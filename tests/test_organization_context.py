import sqlite3

import pytest

from shared.inference_policy import DataClass, InferenceProfile, InferenceProvider
from shared.organization_context import (
    OrganizationContextError,
    assert_organization_inference_allowed,
    resolve_tenant_policy_for_context,
    resolve_trusted_organization_context,
)
from shared.tenant_processing_policy import (
    CloudProcessingRegion,
    TenantProcessingPolicyError,
    ensure_organization_processing_policy_schema,
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
def org_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            email TEXT,
            current_org_id INTEGER
        )
        """
    )
    ensure_organization_processing_policy_schema(conn)
    conn.execute("INSERT INTO users (id, email, current_org_id) VALUES (1, 'owner@example.test', 10)")
    conn.execute("INSERT INTO users (id, email, current_org_id) VALUES (2, 'member@example.test', 10)")
    conn.execute("INSERT INTO users (id, email, current_org_id) VALUES (3, 'other@example.test', 20)")
    conn.execute("INSERT INTO organizations (id, name, slug, cloud_processing_region) VALUES (10, 'EU Org', 'eu-org', 'eu')")
    conn.execute(
        "INSERT INTO organizations (id, name, slug, cloud_processing_region) VALUES (20, 'Local Org', 'local-org', 'local_only')"
    )
    conn.execute("INSERT INTO org_members (org_id, user_id, role) VALUES (10, 1, 'owner')")
    conn.execute("INSERT INTO org_members (org_id, user_id, role) VALUES (10, 2, 'member')")
    conn.execute("INSERT INTO org_members (org_id, user_id, role) VALUES (20, 3, 'owner')")
    conn.execute("CREATE TABLE jobs (job_id TEXT PRIMARY KEY, user_id INTEGER)")
    conn.execute("CREATE TABLE invoices (id INTEGER PRIMARY KEY, job_id TEXT)")
    conn.execute("INSERT INTO jobs (job_id, user_id) VALUES ('job-eu', 1)")
    conn.execute("INSERT INTO jobs (job_id, user_id) VALUES ('job-local', 3)")
    conn.execute("INSERT INTO invoices (id, job_id) VALUES (100, 'job-eu')")
    conn.execute("INSERT INTO invoices (id, job_id) VALUES (200, 'job-local')")
    conn.commit()
    yield conn
    conn.close()


def test_valid_session_membership_resolves_server_side_org(org_db):
    context = resolve_trusted_organization_context(session={"user_id": 1}, connection=org_db)

    assert context is not None
    assert context.organization_id == 10
    assert context.source == "user_current_org"


def test_invoice_from_other_organization_blocks_access(org_db):
    with pytest.raises(OrganizationContextError) as exc_info:
        resolve_trusted_organization_context(
            session={"user_id": 1},
            invoice_id=200,
            connection=org_db,
        )

    assert exc_info.value.error_code == "ORG_CONTEXT_REQUIRED"
    assert exc_info.value.reason_code == "organization_membership_required"


def test_client_body_organization_id_is_rejected(org_db):
    with pytest.raises(OrganizationContextError) as exc_info:
        resolve_trusted_organization_context(
            session={"user_id": 1},
            client_input={"organization_id": 20, "cloud_processing_region": "local_only"},
            connection=org_db,
        )

    assert exc_info.value.reason_code == "client_context_override_denied"


def test_missing_org_in_production_enforcement_blocks_external_provider():
    with pytest.raises(OrganizationContextError) as exc_info:
        assert_organization_inference_allowed(
            organization_context=None,
            data_class=DataClass.INVOICE_CONFIDENTIAL,
            requested_inference_profile=InferenceProfile.STANDARD,
            provider=InferenceProvider.OPENAI_DIRECT,
            env=_prod_env(),
        )

    assert exc_info.value.error_code == "ORG_CONTEXT_REQUIRED"
    assert exc_info.value.reason_code == "organization_context_missing"


def test_development_demo_exception_is_explicitly_allowed():
    context = resolve_trusted_organization_context(
        allow_demo_exception=True,
        demo_flow=True,
        env={"FLOWCHECK_RUNTIME_ENV": "development"},
    )

    assert context is not None
    assert context.demo_flow is True
    profile = assert_organization_inference_allowed(
        organization_context=context,
        data_class=DataClass.DEMO,
        requested_inference_profile=InferenceProfile.STANDARD,
        provider=InferenceProvider.OPENAI_DIRECT,
        allow_demo_exception=True,
        env={"FLOWCHECK_RUNTIME_ENV": "development"},
    )
    assert profile == InferenceProfile.STANDARD


def test_eu_organization_resolves_eu_regional_cloud(org_db):
    context = resolve_trusted_organization_context(session={"user_id": 1}, connection=org_db)
    decision = resolve_tenant_policy_for_context(context, connection=org_db, env=_prod_env())

    assert decision.cloud_processing_region == CloudProcessingRegion.EU
    assert decision.effective_inference_profile == InferenceProfile.EU_REGIONAL_CLOUD
    assert decision.is_external_cloud_allowed is True


def test_local_only_organization_resolves_sovereign(org_db):
    context = resolve_trusted_organization_context(session={"user_id": 3}, connection=org_db)
    decision = resolve_tenant_policy_for_context(context, connection=org_db, env=_prod_env())

    assert decision.cloud_processing_region == CloudProcessingRegion.LOCAL_ONLY
    assert decision.effective_inference_profile == InferenceProfile.SOVEREIGN
    assert decision.is_external_cloud_allowed is False


def test_local_only_without_local_provider_fails_closed(org_db):
    context = resolve_trusted_organization_context(session={"user_id": 3}, connection=org_db)

    with pytest.raises(TenantProcessingPolicyError) as exc_info:
        assert_organization_inference_allowed(
            organization_context=context,
            data_class=DataClass.INVOICE_CONFIDENTIAL,
            requested_inference_profile=InferenceProfile.STANDARD,
            provider=InferenceProvider.LOCAL_OPENAI_COMPAT,
            connection=org_db,
            env=_prod_env(),
            local_provider_available=False,
        )

    assert getattr(exc_info.value, "error_code", "") == "SOVEREIGN_INFERENCE_UNAVAILABLE"
