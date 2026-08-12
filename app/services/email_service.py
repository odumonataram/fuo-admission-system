"""
Email service: wraps Flask-Mail so routes don't need to know about
message construction. Falls back to logging (instead of raising) if
mail is not configured, so the app remains usable in local development
without SMTP credentials.
"""

import logging
from flask import current_app, render_template
from flask_mail import Message

from app.extensions import mail

logger = logging.getLogger(__name__)


def _send(subject: str, recipients: list, html_body: str):
    if not current_app.config.get("MAIL_USERNAME"):
        logger.info("MAIL not configured — skipping send. Subject: %s To: %s", subject, recipients)
        return False

    msg = Message(subject=subject, recipients=recipients, html=html_body)
    try:
        mail.send(msg)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", recipients)
        return False


def send_password_reset_email(user, reset_url: str):
    html = render_template(
        "auth/email/reset_password_email.html", user=user, reset_url=reset_url
    )
    return _send("Reset Your FUO Admission Portal Password", [user.email], html)


def send_welcome_email(user):
    html = render_template("auth/email/welcome_email.html", user=user)
    return _send("Welcome to FUO Admission Portal", [user.email], html)
