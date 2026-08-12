from pathlib import Path


ENV_EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"


def _entries() -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def test_modular_runtime_uses_canonical_database_and_jwt_names():
    env = _entries()
    assert "DATABASE_URL" in env
    assert "JWT_SECRET_KEY" in env
    assert "JWT_SECRET" not in env


def test_legacy_default_tenant_fallback_is_not_documented():
    env = _entries()
    assert "DEFAULT_TENANT_ID" not in env


def test_api_key_requires_explicit_scoped_identity_configuration():
    env = _entries()
    assert "SBS_API_KEY" in env
    assert "SBS_API_KEY_TENANT_ID" in env
    assert "SBS_API_KEY_USER_ID" in env
    assert env["SBS_API_KEY_ROLE"] == "service"


def test_production_example_requires_regional_cloud_governance():
    env = _entries()
    assert env["FLOWCHECK_RUNTIME_ENV"] == "production"
    assert env["FLOWCHECK_REQUIRE_EU_REGIONAL_CLOUD_IN_PRODUCTION"].lower() == "true"
