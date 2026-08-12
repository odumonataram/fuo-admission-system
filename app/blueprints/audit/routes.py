"""Audit blueprint: view audit logs. Phase 7."""

from flask import Blueprint
from flask_login import login_required

audit_bp = Blueprint("audit", __name__)


@audit_bp.route("/")
@login_required
def index():
    return "Audit logs - coming in Phase 7"
