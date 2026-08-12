"""Admission processing blueprint: generate admission lists/letters,
trigger QR code + PDF generation on approval. Phase 5.
"""

from flask import Blueprint
from flask_login import login_required

admission_bp = Blueprint("admission", __name__)


@admission_bp.route("/pending")
@login_required
def pending():
    return "Admission processing - coming in Phase 5"
