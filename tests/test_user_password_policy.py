import pytest

from modules.rechnungsverarbeitung.src.invoices.services.user_service import (
    UserService,
    validate_password_strength,
)


def test_password_policy_accepts_strong_bcrypt_compatible_password():
    validate_password_strength("FlowCheck-2026-Sicher!")


@pytest.mark.parametrize(
    "password",
    [
        "short",
        "password1234",
        "aaaaaaaaaaaa",
        "123456789012",
    ],
)
def test_password_policy_rejects_weak_passwords(password):
    with pytest.raises(ValueError):
        validate_password_strength(password)


def test_password_policy_rejects_values_over_bcrypt_byte_limit():
    # 30 euro signs = 90 UTF-8 bytes, despite only 30 characters.
    with pytest.raises(ValueError, match="72 UTF-8-Bytes"):
        validate_password_strength("€" * 30)


def test_invite_rejects_unknown_role_before_database_access(monkeypatch):
    service = UserService()

    def fail_if_called():
        raise AssertionError("database must not be touched for an invalid role")

    monkeypatch.setattr(
        "modules.rechnungsverarbeitung.src.invoices.services.user_service.get_session",
        fail_if_called,
    )

    with pytest.raises(ValueError, match="Invalid role"):
        service.invite_user(
            email="test@example.invalid",
            password="FlowCheck-2026-Sicher!",
            name="Test User",
            tenant_id="tenant-123",
            role="superadmin",
        )
