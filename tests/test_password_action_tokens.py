import pytest
from fastapi import HTTPException

from modules.rechnungsverarbeitung.src.auth import jwt_auth


@pytest.fixture(autouse=True)
def _test_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-password-action-secret")
    jwt_auth._jwt_secret_cache = None
    yield
    jwt_auth._jwt_secret_cache = None


def test_password_reset_token_is_purpose_bound_and_credential_bound():
    current_hash = "$2b$12$example-current-hash-value"
    token = jwt_auth.create_password_action_token(
        user_id="user-123",
        tenant_id="tenant-123",
        password_hash=current_hash,
        purpose="password_reset",
        expires_minutes=30,
    )

    payload = jwt_auth.decode_password_action_token(token, "password_reset")

    assert payload["sub"] == "user-123"
    assert payload["tenant_id"] == "tenant-123"
    assert payload["type"] == "password_action"
    assert payload["purpose"] == "password_reset"
    assert payload["jti"]
    assert current_hash not in token
    assert jwt_auth.password_action_matches_current_credential(payload, current_hash)


def test_password_action_token_is_invalid_after_password_hash_changes():
    token = jwt_auth.create_password_action_token(
        user_id="user-123",
        tenant_id="tenant-123",
        password_hash="old-password-hash",
        purpose="invite_accept",
    )
    payload = jwt_auth.decode_password_action_token(token, "invite_accept")

    assert not jwt_auth.password_action_matches_current_credential(
        payload,
        "new-password-hash",
    )


def test_password_action_token_cannot_be_reused_for_different_purpose():
    token = jwt_auth.create_password_action_token(
        user_id="user-123",
        tenant_id="tenant-123",
        password_hash="current-password-hash",
        purpose="password_reset",
    )

    with pytest.raises(HTTPException) as exc_info:
        jwt_auth.decode_password_action_token(token, "invite_accept")

    assert exc_info.value.status_code == 401


@pytest.mark.parametrize("purpose", ["", "login", "access", "admin"])
def test_password_action_token_rejects_unsupported_purpose(purpose):
    with pytest.raises(ValueError, match="Unsupported password action purpose"):
        jwt_auth.create_password_action_token(
            user_id="user-123",
            tenant_id="tenant-123",
            password_hash="current-password-hash",
            purpose=purpose,
        )


@pytest.mark.parametrize("expires_minutes", [0, -1, 1441])
def test_password_action_token_rejects_unsafe_expiry(expires_minutes):
    with pytest.raises(ValueError, match="Invalid password action expiry"):
        jwt_auth.create_password_action_token(
            user_id="user-123",
            tenant_id="tenant-123",
            password_hash="current-password-hash",
            purpose="password_reset",
            expires_minutes=expires_minutes,
        )
