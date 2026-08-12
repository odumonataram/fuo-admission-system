"""
Admission letter issuance (Phase 5: QR code generation).

When an application is approved, this service:
  1. Creates the AdmissionLetter record (admission number + reference number).
  2. Creates a VerificationToken (a UUID embedded in a verification URL).
  3. Generates a QR code image encoding that verification URL.

PDF generation for the printable letter itself is deferred to a later
phase (pdf_path stays null until then) — this phase delivers the
scannable QR code that resolves to a public verification page.
"""

from flask import current_app

from app.extensions import db
from app.models import AdmissionLetter, VerificationToken, AcademicSession
from app.services.qrcode_service import generate_qr_code


def issue_admission_letter(decision) -> AdmissionLetter:
    """
    Given a newly-created AdmissionDecision (status=approved), create its
    AdmissionLetter + VerificationToken + QR code, and return the letter.
    """
    application = decision.application

    current_session = AcademicSession.query.filter_by(is_current=True).first()
    session_name = current_session.name if current_session else current_app.config["CURRENT_ACADEMIC_SESSION"]

    sequence = AdmissionLetter.query.count() + 1
    admission_number = AdmissionLetter.generate_admission_number(session_name, sequence)
    reference_number = AdmissionLetter.generate_reference_number()

    letter = AdmissionLetter(
        decision_id=decision.id,
        admission_number=admission_number,
        reference_number=reference_number,
        pdf_path=None,
        qr_code_path="",  # filled in below, once we have a token
    )
    db.session.add(letter)
    db.session.flush()  # assigns letter.id without committing yet

    token = VerificationToken(admission_letter_id=letter.id)
    db.session.add(token)
    db.session.flush()  # assigns token.token (UUID) via its default

    verification_url = token.verification_url(current_app.config["APP_BASE_URL"])
    qr_filename = f"{token.token}.png"
    letter.qr_code_path = generate_qr_code(verification_url, qr_filename)

    db.session.commit()
    return letter
