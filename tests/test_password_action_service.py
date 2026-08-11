from contextlib import contextmanager

import pytest

from modules.rechnungsverarbeitung.src.auth import jwt_auth
from modules.rechnungsverarbeitung.src.auth.password_actions import PasswordActionService


class _Result:
    def __init__(self, row=None, rowcount=0):
        self._row = row
        self.rowcount = rowcount

    def fetchone(self):
        return self._row


class _Session:
    def __init__(self, *, select_row, update_rowcount=1):
        self.select_row = select_row
        self.update_rowcount = update_rowcount
        self.committed = False
        self.rolled_back = False
        self.update_calls = 0

    def execute(self, statement, params):
        sql = str(statement)
        if sql.lstrip().upper().startswith("SELECT"):
            return _Result(row=self.select_row)
        if sql.lstrip().upper().startswith("UPDATE"):
            self.update_calls += 1
            return _Result(rowcount=self.update_rowcount)
        raise AssertionError(f"unexpected SQL: {sql}")

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-password-action-service-secret")
    jwt_auth._jwt_secret_cache = None
    yield
    jwt_auth._jwt_secret_cache = None


def _patch_session(monkeypatch, session):
    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(
        "modules.rechnungsverarbeitung.src.auth.password_actions.get_session",
        fake_get_session,
    )


def test_issue_for_email_does_not_mutate_credential(monkeypatch):
    password_hash = "$2b$12$current-password-hash"
    session = _Session(
        select_row=("user-1", "tenant-1", "User@Example.invalid", password_hash)
    )
    _patch_session(monkeypatch, session)

    issue = PasswordActionService().issue_for_email(
        " user@example.invalid ",
        "password_reset",
    )

    assert issue is not None
    assert issue.user_id == "user-1"
    assert issue.tenant_id == "tenant-1"
    assert issue.email == "User@Example.invalid"
    assert issue.purpose == "password_reset"
    assert session.update_calls == 0
    assert not session.committed

    payload = jwt_auth.decode_password_action_token(issue.token, "password_reset")
    assert jwt_auth.password_action_matches_current_credential(payload, password_hash)


def test_issue_for_unknown_email_returns_none(monkeypatch):
    session = _Session(select_row=None)
    _patch_session(monkeypatch, session)

    issue = PasswordActionService().issue_for_email(
        "missing@example.invalid",
        "password_reset",
    )

    assert issue is None
    assert session.update_calls == 0


def test_consume_updates_password_once_with_compare_and_swap(monkeypatch):
    current_hash = "$2b$12$current-password-hash"
    token = jwt_auth.create_password_action_token(
        user_id="user-1",
        tenant_id="tenant-1",
        password_hash=current_hash,
        purpose="password_reset",
    )
    session = _Session(select_row=(current_hash,), update_rowcount=1)
    _patch_session(monkeypatch, session)

    result = PasswordActionService().consume(
        token,
        "FlowCheck-2026-NeuesPasswort!",
        "password_reset",
    )

    assert result == {
        "user_id": "user-1",
        "tenant_id": "tenant-1",
        "status": "password_updated",
    }
    assert session.update_calls == 1
    assert session.committed
    assert not session.rolled_back


def test_consume_rejects_token_after_credential_changed(monkeypatch):
    token = jwt_auth.create_password_action_token(
        user_id="user-1",
        tenant_id="tenant-1",
        password_hash="old-password-hash",
        purpose="password_reset",
    )
    session = _Session(select_row=("different-current-hash",), update_rowcount=1)
    _patch_session(monkeypatch, session)

    with pytest.raises(ValueError, match="invalid or already used"):
        PasswordActionService().consume(
            token,
            "FlowCheck-2026-NeuesPasswort!",
            "password_reset",
        )

    assert session.update_calls == 0
    assert not session.committed


def test_consume_fails_closed_on_compare_and_swap_race(monkeypatch):
    current_hash = "$2b$12$current-password-hash"
    token = jwt_auth.create_password_action_token(
        user_id="user-1",
        tenant_id="tenant-1",
        password_hash=current_hash,
        purpose="invite_accept",
    )
    session = _Session(select_row=(current_hash,), update_rowcount=0)
    _patch_session(monkeypatch, session)

    with pytest.raises(ValueError, match="invalid or already used"):
        PasswordActionService().consume(
            token,
            "FlowCheck-2026-NeuesPasswort!",
            "invite_accept",
        )

    assert session.update_calls == 1
    assert session.rolled_back
    assert not session.committed
