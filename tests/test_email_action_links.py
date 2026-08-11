import inspect

from modules.rechnungsverarbeitung.src.invoices.services import email_notifications


def test_invite_signature_does_not_accept_temp_password():
    parameters = inspect.signature(email_notifications.EmailService.send_invite).parameters

    assert "temp_password" not in parameters
    assert "action_token" in parameters


def test_invite_email_contains_action_link_but_no_password(monkeypatch):
    service = email_notifications.EmailService()
    captured = {}

    monkeypatch.setattr(email_notifications.resend, "api_key", "test-key")

    def fake_send(payload):
        captured.update(payload)
        return {"id": "email-123"}

    monkeypatch.setattr(email_notifications.resend.Emails, "send", fake_send)

    result = service.send_invite(
        to_email="invitee@example.invalid",
        inviter_name="Admin",
        action_token="sensitive.action.token",
        role="viewer",
    )

    assert result["sent"] is True
    html = captured["html"]
    assert "/auth/accept-invite#token=" in html
    assert "sensitive.action.token" in html
    assert "Temporaeres Passwort" not in html
    assert "Temporäres Passwort" not in html


def test_password_reset_email_contains_action_link_and_no_reusable_credential(monkeypatch):
    service = email_notifications.EmailService()
    captured = {}

    monkeypatch.setattr(email_notifications.resend, "api_key", "test-key")

    def fake_send(payload):
        captured.update(payload)
        return {"id": "email-456"}

    monkeypatch.setattr(email_notifications.resend.Emails, "send", fake_send)

    result = service.send_password_reset(
        to_email="user@example.invalid",
        action_token="reset.action.token",
    )

    assert result["sent"] is True
    html = captured["html"]
    assert "/auth/reset-password#token=" in html
    assert "reset.action.token" in html
    assert "bisheriges Passwort wurde nicht geändert" in html


def test_action_token_is_put_in_fragment_not_query_string():
    url = email_notifications.EmailService._action_url(
        "/auth/reset-password",
        "a token/with+special?chars",
    )

    assert "?token=" not in url
    assert "#token=" in url
    assert "a%20token%2Fwith%2Bspecial%3Fchars" in url


def test_delivery_failure_does_not_return_provider_exception_text(monkeypatch):
    service = email_notifications.EmailService()

    monkeypatch.setattr(email_notifications.resend, "api_key", "test-key")

    def fail_send(_payload):
        raise RuntimeError("provider response contained recipient PII")

    monkeypatch.setattr(email_notifications.resend.Emails, "send", fail_send)

    result = service.send_password_reset(
        to_email="user@example.invalid",
        action_token="reset.action.token",
    )

    assert result == {"sent": False, "reason": "email_delivery_failed"}
    assert "recipient PII" not in str(result)
