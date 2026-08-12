"""Notifications blueprint: in-app notifications. Phase 7."""

from flask import Blueprint
from flask_login import login_required

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/")
@login_required
def index():
    return "Notifications - coming in Phase 7"
