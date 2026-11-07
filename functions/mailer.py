"""Sends email through Gmail SMTP with an app password.

Not named email.py: that would hide Python's own email package, which smtplib imports.

Two settings for testing (plan Phase 5 step 2), both off in normal use:
- MAIL_ALLOWLIST: while set, mail goes only to these addresses (separated by ';', ',' or spaces);
  everyone else is skipped and logged. Deployed during the production test so no real member
  can be emailed, then removed.
- MAIL_MODE=log: log each email instead of sending it. Used with the emulators; needs no SMTP login.
"""
import logging
import os
import re
import smtplib
import ssl
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587  # STARTTLS; Cloud Run blocks port 25 but allows 587

logger = logging.getLogger(__name__)


class MailerNotConfigured(RuntimeError):
    pass


def _allowlist():
    """The allowed addresses, lowercased, or None when MAIL_ALLOWLIST isn't set (everyone is allowed)."""
    value = os.environ.get("MAIL_ALLOWLIST", "").strip()
    return {address.lower() for address in re.split(r"[;,\s]+", value) if address} if value else None


def send(to, subject, body):
    allowed = _allowlist()
    if allowed is not None:
        skipped = [address for address in to if address.lower() not in allowed]
        to = [address for address in to if address.lower() in allowed]
        if skipped:
            logger.warning("MAIL_ALLOWLIST is set: not sending %r to %d address(es) off the list", subject, len(skipped))
        if not to:
            return

    if os.environ.get("MAIL_MODE") == "log":
        logger.warning("MAIL_MODE=log, not sent:\nTo: %s\nSubject: %s\n\n%s", ", ".join(to), subject, body)
        return

    sender = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    if not sender or not password:
        raise MailerNotConfigured("set SMTP_USER and SMTP_PASSWORD (--set-secrets=SMTP_PASSWORD=smtp-password:latest)")

    message = EmailMessage()
    message["From"] = f"Secret Santa <{sender}>"
    message["To"] = ", ".join(to)
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(sender, password)
        smtp.send_message(message)
