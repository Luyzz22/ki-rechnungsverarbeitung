import pytest
from fastapi import HTTPException

from modules.rechnungsverarbeitung.src.auth import jwt_auth


def _set_runtime(monkeypatch, value: str) -> None:
    monkeypatch.setenv("FLOWCHECK_RUNTIME_ENV", value)
    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-secret")
    jwt_auth._jwt_secret_cache = None


def test_reserved_demo_identity_is_blocked_in_production(monkeypatch):
    _set_runtime(monkeypatch, "production")

    with pytest.raises(HTTPException) as exc_info:
        jwt_auth.create_tokens(
            user_id="demo-user",
            tenant_id="test-ai-live",
            role="user",
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid credentials"


def test_reserved_demo_user_is_blocked_even_with_other_tenant(monkeypatch):
    _set_runtime(monkeypatch, "production")

    with pytest.raises(HTTPException) as exc_info:
        jwt_auth.create_access_token(
            user_id="demo-user",
            tenant_id="tenant-other",
            role="user",
        )

    assert exc_info.value.status_code == 401


def test_reserved_demo_tenant_is_blocked_even_with_other_user(monkeypatch):
    _set_runtime(monkeypatch, "production")

    with pytest.raises(HTTPException) as exc_info:
        jwt_auth.create_refresh_token(
            user_id="user-other",
            tenant_id="test-ai-live",
        )

    assert exc_info.value.status_code == 401


def test_reserved_demo_identity_remains_available_in_explicit_test_runtime(monkeypatch):
    _set_runtime(monkeypatch, "test")

    tokens = jwt_auth.create_tokens(
        user_id="demo-user",
        tenant_id="test-ai-live",
        role="user",
    )

    access = jwt_auth.decode_token(tokens.access_token)
    refresh = jwt_auth.decode_token(tokens.refresh_token)
    assert access["sub"] == "demo-user"
    assert access["tenant_id"] == "test-ai-live"
    assert access["type"] == "access"
    assert refresh["type"] == "refresh"


def test_normal_identity_is_allowed_in_production(monkeypatch):
    _set_runtime(monkeypatch, "production")

    tokens = jwt_auth.create_tokens(
        user_id="user-123",
        tenant_id="tenant-123",
        role="admin",
    )

    payload = jwt_auth.decode_token(tokens.access_token)
    assert payload["sub"] == "user-123"
    assert payload["tenant_id"] == "tenant-123"
    assert payload["role"] == "admin"
