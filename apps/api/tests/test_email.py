import httpx

from app import email as email_module


def test_send_email_returns_error_when_api_key_not_configured(monkeypatch):
    monkeypatch.setattr(email_module.settings, "resend_api_key", "")
    error = email_module.send_email("user@example.com", "subject", "<p>hi</p>")
    assert error == "RESEND_API_KEY is not configured"


def test_send_email_returns_none_on_success(monkeypatch):
    monkeypatch.setattr(email_module.settings, "resend_api_key", "test-key")
    monkeypatch.setattr(
        email_module.httpx, "post", lambda *a, **k: httpx.Response(200, json={"id": "abc"})
    )

    error = email_module.send_email("user@example.com", "subject", "<p>hi</p>")
    assert error is None


def test_send_email_returns_error_message_on_resend_failure(monkeypatch):
    monkeypatch.setattr(email_module.settings, "resend_api_key", "test-key")
    monkeypatch.setattr(
        email_module.httpx, "post", lambda *a, **k: httpx.Response(422, text="invalid sender")
    )

    error = email_module.send_email("user@example.com", "subject", "<p>hi</p>")
    assert error is not None
    assert "422" in error


def test_send_email_returns_error_message_on_network_failure(monkeypatch):
    monkeypatch.setattr(email_module.settings, "resend_api_key", "test-key")

    def raise_request_error(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(email_module.httpx, "post", raise_request_error)

    error = email_module.send_email("user@example.com", "subject", "<p>hi</p>")
    assert "Could not reach Resend" in error
