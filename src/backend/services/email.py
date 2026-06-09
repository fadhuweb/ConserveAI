"""Email delivery via SMTP (Gmail).

Used to send a newly provisioned park manager their temporary password, so the
admin never sees it. Configure SMTP_USER and SMTP_PASSWORD (a Gmail App Password)
in the .env file. If SMTP is not configured, send_email raises RuntimeError.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from src.backend.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    """Send a plain-text email. Raises RuntimeError if SMTP is not configured."""
    if not settings.email_enabled:
        raise RuntimeError(
            "SMTP is not configured — set SMTP_USER and SMTP_PASSWORD (a Gmail App Password) in .env"
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context) as server:
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)

    logger.info("Sent email to %s (subject=%r)", to, subject)


def send_temporary_password(to: str, username: str, full_name: str | None, temp_password: str) -> None:
    """Email a new manager their username and temporary password."""
    name = full_name or username
    subject = "Your ConserveAI account"
    body = (
        f"Hello {name},\n\n"
        f"A ConserveAI account has been created for you.\n\n"
        f"  Username:           {username}\n"
        f"  Temporary password: {temp_password}\n\n"
        f"Please sign in and set your own password on first login. "
        f"This temporary password will stop working once you change it.\n\n"
        f"— ConserveAI"
    )
    send_email(to, subject, body)
