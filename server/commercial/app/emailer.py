"""Transactional email via Resend's HTTP API.

In dev_mode (or when no API key is set) emails are logged to stdout
instead of sent, so the app is fully runnable locally without secrets.
"""
import logging

import requests

from .config import get_settings

log = logging.getLogger("commercial.email")
settings = get_settings()


def send_email(to: str, subject: str, html: str, text: str | None = None) -> None:
    if settings.dev_mode or not settings.resend_api_key:
        log.warning("[DEV EMAIL] to=%s subject=%s\n%s", to, subject, text or html)
        return
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        json={"from": settings.email_from, "to": [to], "subject": subject,
              "html": html, **({"text": text} if text else {})},
        timeout=20,
    )
    if resp.status_code >= 300:
        log.error("Resend error %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()


def send_magic_link(to: str, link: str) -> None:
    send_email(
        to,
        "Your deathlessons.org sign-in link",
        f'<p>Click to sign in to deathlessons.org:</p>'
        f'<p><a href="{link}">{link}</a></p>'
        f'<p>This link expires in 15 minutes and can be used once. '
        f'If you didn\'t request it, you can ignore this email.</p>',
        text=f"Sign in to deathlessons.org: {link}\n"
             f"This link expires in 15 minutes and can be used once.",
    )
