import pytest
from fastapi import HTTPException

from modules.rechnungsverarbeitung.src.auth import jwt_auth


def _set_runtime(monkeypatch, value: str) -> None:
    monkeypatch.setenv("FLOWCHECK_RUNTIME_ENV", value)
    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-secret")
    jwt_auth._jwt_secret_cache = None


def _assert_blocked(callable_):
    with pytest.raises(HTTPException) as exc_info:
        callable_()
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid credentials"


def test_reserved_demo_identity_is_blocked_in_production(monkeypatch):
    _set_runtime(monkeypatch, "production")
    _assert_blocked(
        lambda: jwt_auth.create_tokens(
            user_id="demo-user",
            tenant_id="test-ai-live",
            role="user",
        )
    )


def test_reserved_demo_user_is_blocked_even_with_other_tenant(monkeypatch):
    _set_runtime(monkeypatch, "production")
    _assert_blocked(
        lambda: jwt_auth.create_access_token(
            user_id="demo-user",
            tenant_id="tenant-other",
            role="user",
        )
    )


def test_reserved_demo_tenant_is_blocked_even_with_other_user(monkeypatch):
    _set_runtime(monkeypatch, "production")
    _assert_blocked(
        lambda: jwt_auth.create_refresh_token(
            user_id="user-other",
            tenant_id="test-ai-live",
        )
    )


@pytest.mark.parametrize("runtime", ["development", "dev", "test", "ci"])
def test_reserved_demo_identity_is_blocked_in_every_nonproduction_runtime(
    monkeypatch,
    runtime,
):
    _set_runtime(monkeypatch, runtime)
    _assert_blocked(
        lambda: jwt_auth.create_tokens(
            user_id="demo-user",
            tenant_id="test-ai-live",
            role="user",
        )
    )


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
