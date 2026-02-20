import logging

import aiosmtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)

_PLACEHOLDER_VALUES = {"", "your-email@gmail.com", "your-app-password"}


def _smtp_configured() -> bool:
    return (
        settings.SMTP_USER not in _PLACEHOLDER_VALUES
        and settings.SMTP_PASSWORD not in _PLACEHOLDER_VALUES
    )


async def send_verification_email(to: str, code: str) -> None:
    if not _smtp_configured():
        logger.warning("SMTP not configured -- printing code to console")
        logger.warning(">>> Verification code for %s: %s <<<", to, code)
        return

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    message["To"] = to
    message["Subject"] = "FinTrack - Your verification code"
    message.set_content(
        f"Your verification code is: {code}\n\n"
        f"This code expires in {settings.VERIFICATION_CODE_EXPIRE_MINUTES} minutes.\n\n"
        "If you did not request this code, please ignore this email."
    )

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
            timeout=10,
        )
    except Exception:
        logger.exception("Failed to send email via SMTP, falling back to console")
        logger.warning(">>> Verification code for %s: %s <<<", to, code)
