"""Verification blueprint: public QR-scan verification page.

Anyone (no login required) can scan the QR code on an admission letter,
which links here as /verify/<token>. We look up the token, log the
attempt (valid or invalid) for audit purposes, and show a simple result
page — never exposing personal data beyond what's needed to confirm the
admission is genuine.
"""

from flask import Blueprint, render_template, request

from app.extensions import db
from app.models import VerificationToken, VerificationLog

verification_bp = Blueprint("verification", __name__)


@verification_bp.route("/<token>")
def verify(token):
    verification_token = VerificationToken.query.filter_by(token=token).first()
    is_valid = bool(verification_token and verification_token.is_active)

    db.session.add(
        VerificationLog(
            token_id=verification_token.id if verification_token else None,
            token_value_attempted=token,
            result="valid" if is_valid else "invalid",
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
        )
    )
    db.session.commit()

    letter = verification_token.admission_letter if is_valid else None
    return render_template("verification/result.html", is_valid=is_valid, letter=letter)
