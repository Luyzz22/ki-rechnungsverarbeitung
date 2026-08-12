import pytest
from fastapi import HTTPException

from modules.rechnungsverarbeitung.src.auth import jwt_auth


def _clear_api_key_env(monkeypatch) -> None:
    for name in (
        "SBS_API_KEY",
        "SBS_API_KEY_TENANT_ID",
        "SBS_API_KEY_USER_ID",
        "SBS_API_KEY_ROLE",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.asyncio
async def test_matching_api_key_requires_explicit_tenant_scope(monkeypatch):
    _clear_api_key_env(monkeypatch)
    monkeypatch.setenv("SBS_API_KEY", "test-secret")

    with pytest.raises(HTTPException) as exc_info:
        await jwt_auth.get_current_user(credentials=None, api_key="test-secret")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "API key authentication unavailable"


@pytest.mark.asyncio
async def test_matching_api_key_resolves_configured_identity(monkeypatch):
    _clear_api_key_env(monkeypatch)
    monkeypatch.setenv("SBS_API_KEY", "test-secret")
    monkeypatch.setenv("SBS_API_KEY_TENANT_ID", "tenant-123")
    monkeypatch.setenv("SBS_API_KEY_USER_ID", "integration-123")
    monkeypatch.setenv("SBS_API_KEY_ROLE", "service")

    user = await jwt_auth.get_current_user(credentials=None, api_key="test-secret")

    assert user.user_id == "integration-123"
    assert user.tenant_id == "tenant-123"
    assert user.role == "service"


@pytest.mark.asyncio
async def test_matching_api_key_rejects_invalid_role_configuration(monkeypatch):
    _clear_api_key_env(monkeypatch)
    monkeypatch.setenv("SBS_API_KEY", "test-secret")
    monkeypatch.setenv("SBS_API_KEY_TENANT_ID", "tenant-123")
    monkeypatch.setenv("SBS_API_KEY_USER_ID", "integration-123")
    monkeypatch.setenv("SBS_API_KEY_ROLE", "superuser")

    with pytest.raises(HTTPException) as exc_info:
        await jwt_auth.get_current_user(credentials=None, api_key="test-secret")

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_wrong_api_key_does_not_authenticate(monkeypatch):
    _clear_api_key_env(monkeypatch)
    monkeypatch.setenv("SBS_API_KEY", "expected-secret")
    monkeypatch.setenv("SBS_API_KEY_TENANT_ID", "tenant-123")
    monkeypatch.setenv("SBS_API_KEY_USER_ID", "integration-123")
    monkeypatch.setenv("SBS_API_KEY_ROLE", "service")

    with pytest.raises(HTTPException) as exc_info:
        await jwt_auth.get_current_user(credentials=None, api_key="wrong-secret")

    assert exc_info.value.status_code == 401
