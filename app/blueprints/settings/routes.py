"""Settings blueprint: system settings, backup database. Phase 7."""

from flask import Blueprint
from flask_login import login_required

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/")
@login_required
def index():
    return "Settings - coming in Phase 7"
