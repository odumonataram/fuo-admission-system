"""
Application service: business logic for creating, validating, and
submitting an applicant's Application for the current academic session.
"""

import json
from datetime import datetime

from app.extensions import db
from app.models import Application, AcademicSession, UploadedDocument
from app.models.application import ApplicationStatus, DocumentType


REQUIRED_DOCUMENT_TYPES = [
    DocumentType.OLEVEL_RESULT,
    DocumentType.UTME_RESULT_SLIP,
    DocumentType.BIRTH_CERTIFICATE,
]

REQUIRED_OLEVEL_SUBJECTS = 5
CREDIT_GRADES = {"A1", "B2", "B3", "C4", "C5", "C6"}


def get_current_session() -> AcademicSession:
    session = AcademicSession.query.filter_by(is_current=True).first()
    if not session:
        # Fall back to the most recently created session so the app
        # doesn't hard-crash if an admin hasn't flagged one as current yet.
        session = AcademicSession.query.order_by(AcademicSession.id.desc()).first()
    return session


def get_or_create_draft_application(applicant_profile):
    """Return the applicant's application for the current session, creating a draft if needed."""
    session = get_current_session()
    if not session:
        return None, "No academic session is currently open for applications."

    application = Application.query.filter_by(
        applicant_id=applicant_profile.id, academic_session_id=session.id
    ).first()

    if application:
        return application, None

    application = Application(
        application_number=f"DRAFT-{applicant_profile.id}-{session.id}",
        applicant_id=applicant_profile.id,
        academic_session_id=session.id,
        programme_id=None,
        status=ApplicationStatus.DRAFT,
    )
    # programme_id is required (nullable=False) so we can't insert until a
    # programme is chosen — hold off on committing until the form saves it.
    return application, None


def save_academic_details(application: Application, *, programme_id, utme_registration_number,
                           utme_score, utme_subjects, olevel_exam_type, olevel_exam_year,
                           olevel_results):
    application.programme_id = programme_id
    application.utme_registration_number = utme_registration_number
    application.utme_score = utme_score
    application.utme_subjects_json = json.dumps(utme_subjects)
    application.olevel_exam_type = olevel_exam_type
    application.olevel_exam_year = olevel_exam_year
    application.olevel_results_json = json.dumps(olevel_results)

    is_new = application.id is None
    db.session.add(application)
    db.session.flush()

    if is_new or application.application_number.startswith("DRAFT-"):
        session = AcademicSession.query.get(application.academic_session_id)
        sequence = Application.query.filter(
            Application.academic_session_id == session.id,
            ~Application.application_number.like("DRAFT-%"),
        ).count() + 1
        application.application_number = Application.generate_application_number(
            session.name, sequence
        )

    db.session.commit()
    return application


def get_uploaded_document_map(application: Application) -> dict:
    """Return {document_type: UploadedDocument} for quick template lookups."""
    return {doc.document_type: doc for doc in application.documents}


def replace_document(application: Application, document_type: str, file_info: dict):
    from app.services.file_service import delete_file

    existing = UploadedDocument.query.filter_by(
        application_id=application.id, document_type=document_type
    ).first()
    if existing:
        delete_file(existing.file_path)
        db.session.delete(existing)
        db.session.flush()

    doc = UploadedDocument(
        application_id=application.id,
        document_type=document_type,
        original_filename=file_info["original_filename"],
        stored_filename=file_info["stored_filename"],
        file_path=file_info["file_path"],
        file_size_bytes=file_info["file_size_bytes"],
        mime_type=file_info["mime_type"],
    )
    db.session.add(doc)
    db.session.commit()
    return doc


def get_completeness_checklist(applicant_profile, application):
    """Returns a list of (label, is_complete) tuples used on the dashboard and preview page."""
    checklist = []

    checklist.append(("Personal profile completed", bool(applicant_profile.profile_completed)))
    checklist.append(("Passport photograph uploaded", bool(applicant_profile.passport_photo_path)))

    has_programme = bool(application and application.programme_id)
    checklist.append(("Programme selected", has_programme))

    has_utme = bool(application and application.utme_registration_number and application.utme_score)
    checklist.append(("UTME details provided", has_utme))

    has_olevel = bool(application and application.olevel_results_json)
    if has_olevel:
        results = json.loads(application.olevel_results_json)
        filled = [r for r in results if r.get("subject") and r.get("grade")]
        has_olevel = len(filled) >= REQUIRED_OLEVEL_SUBJECTS
    checklist.append((f"At least {REQUIRED_OLEVEL_SUBJECTS} O'Level results provided", has_olevel))

    uploaded_types = {doc.document_type for doc in application.documents} if application else set()
    for doc_type in REQUIRED_DOCUMENT_TYPES:
        label = doc_type.replace("_", " ").title()
        checklist.append((f"{label} uploaded", doc_type in uploaded_types))

    return checklist


def is_ready_to_submit(applicant_profile, application) -> bool:
    if not application or application.id is None:
        return False
    return all(is_complete for _, is_complete in get_completeness_checklist(applicant_profile, application))


def submit_application(application: Application):
    application.status = ApplicationStatus.SUBMITTED
    application.submitted_at = datetime.utcnow()
    db.session.commit()
    return application
