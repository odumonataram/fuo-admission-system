"""
Admission processing models.

AdmissionDecision  - the approve/reject decision on an Application, made by staff.
AdmissionLetter    - generated only for approved decisions; holds the PDF path
                     and admission number.
VerificationToken  - a UUID token embedded (as a URL) inside the QR code.
                     The QR code itself NEVER contains personal data — only
                     https://<domain>/verify/<token>. All personal info is
                     looked up server-side from this token at verify time.
"""

import uuid
from datetime import datetime

from app.extensions import db
from app.models.base import TimestampMixin


class DecisionStatus:
    APPROVED = "approved"
    REJECTED = "rejected"
    CHOICES = [APPROVED, REJECTED]


class AdmissionDecision(db.Model, TimestampMixin):
    __tablename__ = "admission_decisions"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer, db.ForeignKey("applications.id"), unique=True, nullable=False
    )
    decided_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    status = db.Column(db.String(20), nullable=False)  # approved / rejected
    remarks = db.Column(db.Text)
    decided_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    application = db.relationship("Application", back_populates="decision")
    decided_by = db.relationship("User")

    admission_letter = db.relationship(
        "AdmissionLetter",
        back_populates="decision",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<AdmissionDecision App#{self.application_id} {self.status}>"


class AdmissionLetter(db.Model, TimestampMixin):
    __tablename__ = "admission_letters"

    id = db.Column(db.Integer, primary_key=True)
    decision_id = db.Column(
        db.Integer, db.ForeignKey("admission_decisions.id"), unique=True, nullable=False
    )

    admission_number = db.Column(db.String(30), unique=True, nullable=False)
    reference_number = db.Column(db.String(50), unique=True, nullable=False)

    pdf_path = db.Column(db.String(500), nullable=True)  # relative to UPLOAD_FOLDER; PDF generation arrives in a later phase
    qr_code_path = db.Column(db.String(500), nullable=False)

    date_issued = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_revoked = db.Column(db.Boolean, default=False, nullable=False)
    revoked_reason = db.Column(db.Text)

    decision = db.relationship("AdmissionDecision", back_populates="admission_letter")
    verification_token = db.relationship(
        "VerificationToken",
        back_populates="admission_letter",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @staticmethod
    def generate_admission_number(session_name: str, sequence: int) -> str:
        year_part = session_name.split("/")[0]
        return f"FUO/ADM/{year_part}/{sequence:05d}"

    @staticmethod
    def generate_reference_number() -> str:
        return f"REF-{uuid.uuid4().hex[:10].upper()}"

    def __repr__(self):
        return f"<AdmissionLetter {self.admission_number}>"


class VerificationToken(db.Model, TimestampMixin):
    """
    The UUID token that is embedded in the QR code as part of a verification
    URL: https://<domain>/verify/<token>.

    IMPORTANT: this table is the ONLY place the token is stored server-side.
    The QR image itself carries no personal data whatsoever.
    """

    __tablename__ = "verification_tokens"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(
        db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()),
        index=True,
    )
    admission_letter_id = db.Column(
        db.Integer, db.ForeignKey("admission_letters.id"), unique=True, nullable=False
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    admission_letter = db.relationship("AdmissionLetter", back_populates="verification_token")
    verification_logs = db.relationship(
        "VerificationLog", back_populates="token", cascade="all, delete-orphan"
    )

    def verification_url(self, base_url: str) -> str:
        return f"{base_url.rstrip('/')}/verify/{self.token}"

    def __repr__(self):
        return f"<VerificationToken {self.token}>"
