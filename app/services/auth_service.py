"""
Auth service: business logic kept out of routes so it's testable and
reusable (e.g. from CLI commands or the admin "create user" flow later).
"""

import secrets
from datetime import datetime, timedelta

from app.extensions import db
from app.models import User, Role, ApplicantProfile
from app.models.audit import AuditLog

RESET_TOKEN_BYTES = 32
RESET_TOKEN_EXPIRY_MINUTES = 30

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def register_applicant(*, first_name, last_name, email, phone_number, password):
    """Create a new User (role=applicant) + linked ApplicantProfile."""
    applicant_role = Role.query.filter_by(name="applicant").first()
    if not applicant_role:
        raise RuntimeError(
            "The 'applicant' role does not exist. Run `flask seed-roles` first."
        )

    user = User(
        email=email.lower().strip(),
        phone_number=phone_number.strip(),
        role=applicant_role,
        is_active=True,
        is_verified=False,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # obtain user.id before creating the profile

    profile = ApplicantProfile(
        user_id=user.id,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
    )
    db.session.add(profile)
    db.session.commit()
    return user


def authenticate(email: str, password: str):
    """
    Attempt to authenticate a user.

    Returns a tuple (user_or_none, error_message_or_none).
    Handles account lockout after repeated failed attempts.
    """
    user = User.query.filter_by(email=email.lower().strip()).first()

    if not user:
        # Deliberately generic message — do not reveal whether the email exists.
        return None, "Invalid email or password."

    if user.is_locked():
        minutes_left = max(
            1, int((user.locked_until - datetime.utcnow()).total_seconds() // 60)
        )
        return None, f"Account temporarily locked. Try again in {minutes_left} minute(s)."

    if not user.is_active:
        return None, "This account has been deactivated. Contact the admissions office."

    if not user.check_password(password):
        user.register_failed_login(
            max_attempts=MAX_FAILED_LOGIN_ATTEMPTS, lock_minutes=LOCKOUT_MINUTES
        )
        db.session.commit()
        return None, "Invalid email or password."

    return user, None


def generate_password_reset_token(user: User) -> str:
    token = secrets.token_urlsafe(RESET_TOKEN_BYTES)
    user.reset_token = token
    user.reset_token_expires_at = datetime.utcnow() + timedelta(
        minutes=RESET_TOKEN_EXPIRY_MINUTES
    )
    db.session.commit()
    return token


def verify_password_reset_token(token: str):
    """Return the User if the token is valid and unexpired, else None."""
    if not token:
        return None
    user = User.query.filter_by(reset_token=token).first()
    if not user:
        return None
    if not user.reset_token_expires_at or user.reset_token_expires_at < datetime.utcnow():
        return None
    return user


def complete_password_reset(user: User, new_password: str):
    user.set_password(new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    user.failed_login_attempts = 0
    user.locked_until = None
    db.session.commit()


def log_action(actor_id, action, entity_type=None, entity_id=None, description=None,
                ip_address=None, user_agent=None):
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.session.add(entry)
    db.session.commit()
