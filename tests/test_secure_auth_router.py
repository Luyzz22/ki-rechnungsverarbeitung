from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from slowapi.errors import RateLimitExceeded

from modules.rechnungsverarbeitung.src.api import secure_auth_router as secure
from modules.rechnungsverarbeitung.src.auth.jwt_auth import TokenResponse, UserAuth, get_current_user
from modules.rechnungsverarbeitung.src.auth.rate_limiter import limiter, rate_limit_handler


@pytest.fixture
def app():
    test_app = FastAPI()
    test_app.state.limiter = limiter
    test_app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    test_app.include_router(secure.router, prefix="/api/v1")
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_login_is_database_backed_and_returns_tokens(monkeypatch, client):
    expected = TokenResponse(access_token="access", refresh_token="refresh")
    calls = {}

    def fake_login(*, email, password):
        calls.update(email=email, password=password)
        return {"tokens": expected, "user": {"id": "user-1"}}

    monkeypatch.setattr(secure._user_service, "login", fake_login)

    response = client.post(
        "/api/v1/auth/token",
        json={"email": "user@example.invalid", "password": "Strong-Password-2026!"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "access"
    assert calls == {
        "email": "user@example.invalid",
        "password": "Strong-Password-2026!",
    }


def test_login_does_not_leak_authentication_failure_details(monkeypatch, client):
    def fail_login(**_kwargs):
        raise ValueError("database-specific authentication detail")

    monkeypatch.setattr(secure._user_service, "login", fail_login)
    response = client.post(
        "/api/v1/auth/token",
        json={"email": "user@example.invalid", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


def test_forgot_password_unknown_account_is_generic_and_sends_nothing(monkeypatch, client):
    monkeypatch.setattr(secure._password_actions, "issue_for_email", lambda *_args: None)

    def fail_send(**_kwargs):
        raise AssertionError("email must not be sent for an unknown account")

    monkeypatch.setattr(secure._email_service, "send_password_reset", fail_send)

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "unknown@example.invalid"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": secure._GENERIC_RECOVERY_MESSAGE}


def test_forgot_password_sends_action_token_without_password_mutation(monkeypatch, client):
    issue = SimpleNamespace(
        user_id="user-1",
        tenant_id="tenant-1",
        email="user@example.invalid",
        token="single-use-reset-token",
        purpose="password_reset",
    )
    issued = {}
    sent = {}

    def fake_issue(email, purpose):
        issued.update(email=email, purpose=purpose)
        return issue

    def fake_send(**kwargs):
        sent.update(kwargs)
        return {"sent": True}

    monkeypatch.setattr(secure._password_actions, "issue_for_email", fake_issue)
    monkeypatch.setattr(secure._email_service, "send_password_reset", fake_send)

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "USER@example.invalid"},
    )

    assert response.status_code == 200
    assert issued == {"email": "USER@example.invalid", "purpose": "password_reset"}
    assert sent == {
        "to_email": "user@example.invalid",
        "action_token": "single-use-reset-token",
    }
    assert "password" not in sent


@pytest.mark.parametrize(
    ("path", "purpose"),
    [
        ("/api/v1/auth/reset-password", "password_reset"),
        ("/api/v1/auth/accept-invite", "invite_accept"),
    ],
)
def test_password_action_endpoints_use_exact_purpose(monkeypatch, client, path, purpose):
    calls = {}

    def fake_consume(*, token, new_password, purpose):
        calls.update(token=token, new_password=new_password, purpose=purpose)
        return {"status": "password_updated"}

    monkeypatch.setattr(secure._password_actions, "consume", fake_consume)

    response = client.post(
        path,
        json={"token": "one-time-token", "new_password": "FlowCheck-2026-Sicher!"},
    )

    assert response.status_code == 200
    assert calls == {
        "token": "one-time-token",
        "new_password": "FlowCheck-2026-Sicher!",
        "purpose": purpose,
    }


def test_invite_request_forbids_client_supplied_password():
    with pytest.raises(ValidationError):
        secure.InviteRequest(
            email="invitee@example.invalid",
            name="Invitee",
            role="editor",
            password="admin-chosen-password",
        )


def test_invite_requires_admin(monkeypatch, app):
    app.dependency_overrides[get_current_user] = lambda: UserAuth(
        user_id="viewer-1",
        tenant_id="tenant-1",
        role="viewer",
    )
    client = TestClient(app)

    def fail_if_called(**_kwargs):
        raise AssertionError("user creation must not run for non-admin")

    monkeypatch.setattr(secure._user_service, "invite_user", fail_if_called)
    response = client.post(
        "/api/v1/users/invite",
        json={"email": "invitee@example.invalid", "name": "Invitee", "role": "editor"},
    )

    assert response.status_code == 403


def test_invite_never_returns_or_emails_bootstrap_secret(monkeypatch, app):
    app.dependency_overrides[get_current_user] = lambda: UserAuth(
        user_id="admin-1",
        tenant_id="tenant-1",
        role="admin",
    )
    client = TestClient(app)
    captured = {}

    def fake_invite_user(*, email, password, name, tenant_id, role):
        captured["bootstrap_secret"] = password
        assert len(password) >= 32
        return {
            "user_id": "invitee-1",
            "tenant_id": tenant_id,
            "email": email.lower(),
            "role": role,
        }

    def fake_issue(email, purpose):
        assert purpose == "invite_accept"
        return SimpleNamespace(
            user_id="invitee-1",
            tenant_id="tenant-1",
            email=email.lower(),
            token="invite-action-token",
            purpose=purpose,
        )

    def fake_send_invite(**kwargs):
        captured["mail"] = kwargs
        return {"sent": True}

    monkeypatch.setattr(secure._user_service, "invite_user", fake_invite_user)
    monkeypatch.setattr(secure._password_actions, "issue_for_email", fake_issue)
    monkeypatch.setattr(secure._email_service, "send_invite", fake_send_invite)

    response = client.post(
        "/api/v1/users/invite",
        json={"email": "Invitee@example.invalid", "name": "Invitee", "role": "editor"},
    )

    assert response.status_code == 200
    payload = response.json()
    bootstrap_secret = captured["bootstrap_secret"]
    assert "temp_password" not in payload
    assert "password" not in payload
    assert bootstrap_secret not in str(payload)
    assert captured["mail"]["action_token"] == "invite-action-token"
    assert bootstrap_secret not in str(captured["mail"])


def test_invite_delivery_failure_removes_inaccessible_account(monkeypatch, app):
    app.dependency_overrides[get_current_user] = lambda: UserAuth(
        user_id="admin-1",
        tenant_id="tenant-1",
        role="admin",
    )
    client = TestClient(app)
    deleted = {}

    monkeypatch.setattr(
        secure._user_service,
        "invite_user",
        lambda **kwargs: {
            "user_id": "invitee-1",
            "tenant_id": kwargs["tenant_id"],
            "email": kwargs["email"].lower(),
            "role": kwargs["role"],
        },
    )
    monkeypatch.setattr(
        secure._password_actions,
        "issue_for_email",
        lambda email, purpose: SimpleNamespace(
            user_id="invitee-1",
            tenant_id="tenant-1",
            email=email.lower(),
            token="invite-action-token",
            purpose=purpose,
        ),
    )
    monkeypatch.setattr(secure._email_service, "send_invite", lambda **_kwargs: {"sent": False})

    def fake_delete_user(*, admin_tenant_id, target_user_id):
        deleted.update(tenant_id=admin_tenant_id, user_id=target_user_id)
        return {"deleted": target_user_id}

    monkeypatch.setattr(secure._user_service, "delete_user", fake_delete_user)

    response = client.post(
        "/api/v1/users/invite",
        json={"email": "invitee@example.invalid", "name": "Invitee", "role": "editor"},
    )

    assert response.status_code == 503
    assert deleted == {"tenant_id": "tenant-1", "user_id": "invitee-1"}
