"""Sends email through Gmail SMTP with an app password.

Not named email.py: that would hide Python's own email package, which smtplib imports.
"""
import os
import smtplib
import ssl
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587  # STARTTLS; Cloud Run blocks port 25 but allows 587


class MailerNotConfigured(RuntimeError):
    pass


def send(to, subject, body):
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
