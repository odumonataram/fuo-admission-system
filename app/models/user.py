"""
User & Role models.

A single `users` table serves both applicants and staff (admin, registrar,
super-admin). Role-based access control is implemented via the `Role`
table plus helper properties on `User`.
"""

import uuid
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db, login_manager
from app.models.base import TimestampMixin


class Role(db.Model, TimestampMixin):
    """
    Roles: applicant, admin, super_admin, registrar.
    Kept as a table (rather than a hard-coded enum) so new roles can be
    added by a super-admin without a schema migration.
    """

    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))

    users = db.relationship("User", back_populates="role", lazy="dynamic")

    def __repr__(self):
        return f"<Role {self.name}>"


class User(db.Model, UserMixin, TimestampMixin):
    """
    Core authentication entity.

    Applicants and staff both log in through this table; `role_id`
    determines what they can access. Applicant-specific data (bio-data,
    passport, etc.) lives in ApplicantProfile, linked 1-to-1.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(
        db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )

    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    role = db.relationship("Role", back_populates="users")

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)

    # Password reset
    reset_token = db.Column(db.String(255), nullable=True, index=True)
    reset_token_expires_at = db.Column(db.DateTime, nullable=True)

    # Login security tracking
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(45), nullable=True)

    # Relationships
    applicant_profile = db.relationship(
        "ApplicantProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    audit_logs = db.relationship("AuditLog", back_populates="actor", lazy="dynamic")
    notifications = db.relationship(
        "Notification", back_populates="recipient", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # --- Password helpers ---
    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    # --- Role helpers ---
    @property
    def role_name(self) -> str:
        return self.role.name if self.role else ""

    def has_role(self, *role_names) -> bool:
        return self.role_name in role_names

    @property
    def is_admin(self) -> bool:
        return self.has_role("admin", "super_admin")

    @property
    def is_super_admin(self) -> bool:
        return self.has_role("super_admin")

    @property
    def is_applicant(self) -> bool:
        return self.has_role("applicant")

    # --- Account lock helpers (brute-force protection) ---
    def is_locked(self) -> bool:
        return bool(self.locked_until and self.locked_until > datetime.utcnow())

    def register_failed_login(self, max_attempts: int = 5, lock_minutes: int = 15):
        from datetime import timedelta

        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = datetime.utcnow() + timedelta(minutes=lock_minutes)

    def register_successful_login(self, ip_address: str = None):
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = datetime.utcnow()
        self.last_login_ip = ip_address

    def __repr__(self):
        return f"<User {self.email} ({self.role_name})>"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
