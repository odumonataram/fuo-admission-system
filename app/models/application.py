"""
Application: a single applicant's submission for one academic session,
including UTME details and programme choice.

UploadedDocument: supporting documents (O-level result, UTME result slip,
birth certificate, etc.) attached to an application.
"""

import uuid
from app.extensions import db
from app.models.base import TimestampMixin


class ApplicationStatus:
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"

    CHOICES = [DRAFT, SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED]


class Application(db.Model, TimestampMixin):
    __tablename__ = "applications"
    __table_args__ = (
        db.UniqueConstraint(
            "applicant_id", "academic_session_id", name="uq_one_application_per_session"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    application_number = db.Column(db.String(30), unique=True, nullable=False)

    applicant_id = db.Column(
        db.Integer, db.ForeignKey("applicant_profiles.id"), nullable=False
    )
    academic_session_id = db.Column(
        db.Integer, db.ForeignKey("academic_sessions.id"), nullable=False
    )
    programme_id = db.Column(db.Integer, db.ForeignKey("programmes.id"), nullable=False)

    # UTME details
    utme_registration_number = db.Column(db.String(30))
    utme_score = db.Column(db.Integer)
    utme_subjects_json = db.Column(db.Text)  # JSON-encoded list of {subject, score}

    # O'Level details (kept simple; can be normalized further later)
    olevel_exam_type = db.Column(db.String(30))  # WAEC, NECO, NABTEB
    olevel_exam_year = db.Column(db.Integer)
    olevel_results_json = db.Column(db.Text)  # JSON-encoded list of {subject, grade}

    status = db.Column(
        db.String(20), default=ApplicationStatus.DRAFT, nullable=False, index=True
    )
    submitted_at = db.Column(db.DateTime, nullable=True)

    applicant = db.relationship("ApplicantProfile", back_populates="applications")
    academic_session = db.relationship("AcademicSession", back_populates="applications")
    programme = db.relationship("Programme", back_populates="applications")

    documents = db.relationship(
        "UploadedDocument", back_populates="application", cascade="all, delete-orphan"
    )
    decision = db.relationship(
        "AdmissionDecision",
        back_populates="application",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @staticmethod
    def generate_application_number(session_name: str, sequence: int) -> str:
        year_part = session_name.split("/")[0]
        return f"FUO/APP/{year_part}/{sequence:06d}"

    def __repr__(self):
        return f"<Application {self.application_number} ({self.status})>"


class DocumentType:
    OLEVEL_RESULT = "olevel_result"
    UTME_RESULT_SLIP = "utme_result_slip"
    BIRTH_CERTIFICATE = "birth_certificate"
    LGA_CERTIFICATE = "lga_certificate"
    PASSPORT_PHOTO = "passport_photo"
    OTHER = "other"

    CHOICES = [
        OLEVEL_RESULT,
        UTME_RESULT_SLIP,
        BIRTH_CERTIFICATE,
        LGA_CERTIFICATE,
        PASSPORT_PHOTO,
        OTHER,
    ]


class UploadedDocument(db.Model, TimestampMixin):
    __tablename__ = "uploaded_documents"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(
        db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    application_id = db.Column(
        db.Integer, db.ForeignKey("applications.id"), nullable=False
    )
    document_type = db.Column(db.String(30), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)  # relative to UPLOAD_FOLDER
    file_size_bytes = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))

    application = db.relationship("Application", back_populates="documents")

    def __repr__(self):
        return f"<UploadedDocument {self.document_type} for App#{self.application_id}>"
