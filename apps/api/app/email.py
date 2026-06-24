import httpx

from app.config import settings

RESEND_API_URL = "https://api.resend.com/emails"


def send_email(to: str, subject: str, html: str) -> str | None:
    """Sends one email via Resend's REST API directly (no SDK dependency,
    same approach as N8nClient). Returns None on success, or an error
    message on failure - never raises, so the alert pipeline can keep going
    for other workflows even if one send fails."""
    if not settings.resend_api_key:
        return "RESEND_API_KEY is not configured"

    try:
        response = httpx.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={"from": settings.alerts_from_email, "to": [to], "subject": subject, "html": html},
            timeout=10.0,
        )
    except httpx.RequestError as exc:
        return f"Could not reach Resend: {exc}"

    if response.status_code >= 400:
        return f"Resend returned {response.status_code}: {response.text[:300]}"

    return None
