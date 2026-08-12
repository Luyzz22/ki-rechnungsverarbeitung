import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from modules.rechnungsverarbeitung.src.auth import jwt_auth


def _set_test_secret(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-secret")
    jwt_auth._jwt_secret_cache = None


@pytest.mark.asyncio
async def test_tenant_header_cannot_replace_missing_auth(monkeypatch):
    _set_test_secret(monkeypatch)

    with pytest.raises(HTTPException) as exc_info:
        await jwt_auth.get_tenant_from_auth(
            credentials=None,
            api_key=None,
            x_tenant_id="attacker-selected-tenant",
        )

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_tenant_is_canonical(monkeypatch):
    _set_test_secret(monkeypatch)
    token = jwt_auth.create_access_token(
        user_id="user-123",
        tenant_id="tenant-123",
        role="user",
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    tenant_id = await jwt_auth.get_tenant_from_auth(
        credentials=credentials,
        api_key=None,
        x_tenant_id=None,
    )

    assert tenant_id == "tenant-123"


@pytest.mark.asyncio
async def test_matching_tenant_header_is_allowed(monkeypatch):
    _set_test_secret(monkeypatch)
    token = jwt_auth.create_access_token(
        user_id="user-123",
        tenant_id="tenant-123",
        role="user",
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    tenant_id = await jwt_auth.get_tenant_from_auth(
        credentials=credentials,
        api_key=None,
        x_tenant_id="tenant-123",
    )

    assert tenant_id == "tenant-123"


@pytest.mark.asyncio
async def test_mismatching_tenant_header_is_rejected(monkeypatch):
    _set_test_secret(monkeypatch)
    token = jwt_auth.create_access_token(
        user_id="user-123",
        tenant_id="tenant-123",
        role="user",
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await jwt_auth.get_tenant_from_auth(
            credentials=credentials,
            api_key=None,
            x_tenant_id="tenant-other",
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "X-Tenant-ID does not match authenticated tenant"
