"""
Application service.

Handles applicant applications, academic details, document uploads,
application completeness, and submission.

Applications are NOT restricted by academic-session opening/closing dates.
Applicants can register and submit applications at any time.
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

CREDIT_GRADES = {
    "A1",
    "B2",
    "B3",
    "C4",
    "C5",
    "C6",
}


def get_current_session():
    """
    Return the current academic session if one exists.

    Academic sessions are no longer required for applicants to register.
    If no session exists, return None instead of blocking registration.
    """

    session = AcademicSession.query.filter_by(
        is_current=True
    ).first()

    if session:
        return session

    return AcademicSession.query.order_by(
        AcademicSession.id.desc()
    ).first()


def get_or_create_draft_application(applicant_profile):
    """
    Return the applicant's draft application.

    Applicants can register at any time. An academic session is used when
    available, but the absence of a session does not prevent registration.
    """

    session = get_current_session()

    # ---------------------------------------------------------
    # If an application already exists for the applicant,
    # return it.
    # ---------------------------------------------------------

    existing_application = (
        Application.query
        .filter_by(applicant_id=applicant_profile.id)
        .order_by(Application.id.desc())
        .first()
    )

    if existing_application:
        return existing_application, None

    # ---------------------------------------------------------
    # An Application requires academic_session_id in the current
    # database schema. Therefore, if no session exists, we cannot
    # create an Application record yet.
    #
    # We return a clear message rather than crashing.
    # ---------------------------------------------------------

    if not session:
        return (
            None,
            "No academic session is available. "
            "Please ask an administrator to create an academic session."
        )

    # ---------------------------------------------------------
    # Create a new draft application.
    # ---------------------------------------------------------

    application = Application(
        application_number=f"DRAFT-{applicant_profile.id}-{session.id}",
        applicant_id=applicant_profile.id,
        academic_session_id=session.id,
        programme_id=None,
        status=ApplicationStatus.DRAFT,
    )

    # programme_id may be nullable=False in the database, so we cannot
    # commit this record until the applicant selects a programme.
    #
    # The application object is returned to the caller and will be
    # persisted by save_academic_details() after programme selection.

    return application, None


def save_academic_details(
    application: Application,
    *,
    programme_id,
    utme_registration_number,
    utme_score,
    utme_subjects,
    olevel_exam_type,
    olevel_exam_year,
    olevel_results,
):
    """
    Save the applicant's programme, UTME and O'Level information.
    """

    application.programme_id = programme_id

    application.utme_registration_number = (
        utme_registration_number
    )

    application.utme_score = utme_score

    application.utme_subjects_json = json.dumps(
        utme_subjects
    )

    application.olevel_exam_type = (
        olevel_exam_type
    )

    application.olevel_exam_year = (
        olevel_exam_year
    )

    application.olevel_results_json = json.dumps(
        olevel_results
    )

    # Determine whether this is a new application.
    is_new = application.id is None

    db.session.add(application)

    # Flush so SQLAlchemy assigns an ID.
    db.session.flush()

    # ---------------------------------------------------------
    # Generate the real application number.
    # ---------------------------------------------------------

    if (
        is_new
        or application.application_number.startswith("DRAFT-")
    ):
        session = AcademicSession.query.get(
            application.academic_session_id
        )

        if session:
            sequence = (
                Application.query
                .filter(
                    Application.academic_session_id
                    == session.id,
                    ~Application.application_number.like(
                        "DRAFT-%"
                    ),
                )
                .count()
                + 1
            )

            application.application_number = (
                Application.generate_application_number(
                    session.name,
                    sequence,
                )
            )
        else:
            # Fallback in the unlikely event that the session was
            # removed after the application was created.
            application.application_number = (
                f"APP-{application.id}"
            )

    db.session.commit()

    return application


def get_uploaded_document_map(application: Application) -> dict:
    """
    Return a dictionary of uploaded documents indexed by document type.
    """

    return {
        document.document_type: document
        for document in application.documents
    }


def replace_document(
    application: Application,
    document_type: str,
    file_info: dict,
):
    """
    Replace an existing uploaded document with a new file.
    """

    from app.services.file_service import delete_file

    existing = (
        UploadedDocument.query
        .filter_by(
            application_id=application.id,
            document_type=document_type,
        )
        .first()
    )

    if existing:
        delete_file(existing.file_path)

        db.session.delete(existing)

        db.session.flush()

    document = UploadedDocument(
        application_id=application.id,
        document_type=document_type,
        original_filename=file_info["original_filename"],
        stored_filename=file_info["stored_filename"],
        file_path=file_info["file_path"],
        file_size_bytes=file_info["file_size_bytes"],
        mime_type=file_info["mime_type"],
    )

    db.session.add(document)

    db.session.commit()

    return document


def get_completeness_checklist(
    applicant_profile,
    application,
):
    """
    Return a list of (label, is_complete) tuples.
    """

    checklist = []

    # ---------------------------------------------------------
    # Applicant profile
    # ---------------------------------------------------------

    checklist.append(
        (
            "Personal profile completed",
            bool(
                applicant_profile.profile_completed
            ),
        )
    )

    # ---------------------------------------------------------
    # Passport photograph
    # ---------------------------------------------------------

    checklist.append(
        (
            "Passport photograph uploaded",
            bool(
                applicant_profile.passport_photo_path
            ),
        )
    )

    # ---------------------------------------------------------
    # Programme
    # ---------------------------------------------------------

    has_programme = bool(
        application
        and application.programme_id
    )

    checklist.append(
        (
            "Programme selected",
            has_programme,
        )
    )

    # ---------------------------------------------------------
    # UTME
    # ---------------------------------------------------------

    has_utme = bool(
        application
        and application.utme_registration_number
        and application.utme_score is not None
    )

    checklist.append(
        (
            "UTME details provided",
            has_utme,
        )
    )

    # ---------------------------------------------------------
    # O'Level results
    # ---------------------------------------------------------

    has_olevel = bool(
        application
        and application.olevel_results_json
    )

    if has_olevel:
        try:
            results = json.loads(
                application.olevel_results_json
            )

            filled = [
                result
                for result in results
                if result.get("subject")
                and result.get("grade")
            ]

            has_olevel = (
                len(filled)
                >= REQUIRED_OLEVEL_SUBJECTS
            )

        except (TypeError, ValueError):
            has_olevel = False

    checklist.append(
        (
            f"At least {REQUIRED_OLEVEL_SUBJECTS} "
            "O'Level results provided",
            has_olevel,
        )
    )

    # ---------------------------------------------------------
    # Required documents
    # ---------------------------------------------------------

    uploaded_types = (
        {
            document.document_type
            for document in application.documents
        }
        if application
        else set()
    )

    for document_type in REQUIRED_DOCUMENT_TYPES:
        label = (
            document_type
            .replace("_", " ")
            .title()
        )

        checklist.append(
            (
                f"{label} uploaded",
                document_type in uploaded_types,
            )
        )

    return checklist


def is_ready_to_submit(
    applicant_profile,
    application,
) -> bool:
    """
    Return True only when all required application sections
    have been completed.
    """

    if not application:
        return False

    if application.id is None:
        return False

    return all(
        is_complete
        for _, is_complete
        in get_completeness_checklist(
            applicant_profile,
            application,
        )
    )


def submit_application(
    application: Application,
):
    """
    Submit an applicant's application.

    There is no academic-session date restriction.
    """

    application.status = (
        ApplicationStatus.SUBMITTED
    )

    application.submitted_at = datetime.utcnow()

    db.session.commit()

    return application