import os
import httpx
from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
# During testing Resend allows sending from onboarding@resend.dev to your own
# account email without verifying a domain. Override with a verified sender in prod.
RESEND_FROM = os.getenv("RESEND_FROM", "Academic Assistant <onboarding@resend.dev>")


def send_reset_email(to_email, reset_link):
    """Send a password-reset email via Resend. Raises on failure so the caller
    can log it (the API endpoint never leaks whether the address exists)."""
    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY is not set")

    html = (
        "<div style=\"font-family:Arial,sans-serif;max-width:480px;margin:auto\">"
        "<h2>Reset your password</h2>"
        "<p>We received a request to reset your Academic Assistant password. "
        "Click the button below to choose a new one. This link expires in 30 minutes.</p>"
        f"<p><a href=\"{reset_link}\" style=\"display:inline-block;background:#2563eb;"
        "color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none\">"
        "Reset password</a></p>"
        f"<p style=\"color:#666;font-size:12px\">Or paste this link: {reset_link}</p>"
        "<p style=\"color:#666;font-size:12px\">If you didn't request this, you can "
        "safely ignore this email.</p>"
        "</div>"
    )

    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={
            "from": RESEND_FROM,
            "to": [to_email],
            "subject": "Reset your Academic Assistant password",
            "html": html,
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()
