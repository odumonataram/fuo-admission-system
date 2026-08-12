"""Reports blueprint: PDF/Excel/CSV exports. Phase 7."""

from flask import Blueprint
from flask_login import login_required

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/")
@login_required
def index():
    return "Reports - coming in Phase 7"
