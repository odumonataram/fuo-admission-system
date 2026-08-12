"""
Models package.

Import every model here so that Flask-Migrate's autogenerate can discover
all tables via `from app.models import *` inside the app factory.
"""

from app.models.user import User, Role
from app.models.academic import Faculty, Department, Programme, AcademicSession
from app.models.applicant import ApplicantProfile
from app.models.application import Application, UploadedDocument
from app.models.admission import AdmissionDecision, AdmissionLetter, VerificationToken
from app.models.verification_log import VerificationLog
from app.models.audit import AuditLog
from app.models.notification import Notification
from app.models.settings import SystemSetting

__all__ = [
    "User",
    "Role",
    "Faculty",
    "Department",
    "Programme",
    "AcademicSession",
    "ApplicantProfile",
    "Application",
    "UploadedDocument",
    "AdmissionDecision",
    "AdmissionLetter",
    "VerificationToken",
    "VerificationLog",
    "AuditLog",
    "Notification",
    "SystemSetting",
]
