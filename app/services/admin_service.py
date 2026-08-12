"""
Admin service: dashboard statistics, applicant search/filtering, and
admission decision (approve/reject) business logic.
"""

from datetime import datetime, timedelta

from sqlalchemy import func, or_

from app.extensions import db
from app.models import (
    User,
    ApplicantProfile,
    Application,
    Programme,
    Department,
    Faculty,
    Notification,
    AdmissionDecision,
)
from app.models.application import ApplicationStatus
from app.models.admission import DecisionStatus
from app.models.notification import NotificationType


# --- Dashboard stats ---

def get_dashboard_stats(session_id=None):
    query = Application.query
    if session_id:
        query = query.filter(Application.academic_session_id == session_id)

    total_applicants = query.count()
    pending = query.filter(
        Application.status.in_([ApplicationStatus.SUBMITTED, ApplicationStatus.UNDER_REVIEW])
    ).count()
    approved = query.filter(Application.status == ApplicationStatus.APPROVED).count()
    rejected = query.filter(Application.status == ApplicationStatus.REJECTED).count()

    from app.models import AdmissionLetter, VerificationLog
    letters_generated = AdmissionLetter.query.count()
    qr_verifications = VerificationLog.query.count()

    recent_applications = (
        query.filter(Application.status != ApplicationStatus.DRAFT)
        .order_by(Application.submitted_at.desc())
        .limit(8)
        .all()
    )

    return {
        "total_applicants": total_applicants,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "letters_generated": letters_generated,
        "qr_verifications": qr_verifications,
        "recent_applications": recent_applications,
    }


def get_monthly_application_counts(months_back=6):
    """Returns two aligned lists: month labels and submission counts, for Chart.js."""
    today = datetime.utcnow().replace(day=1)
    buckets = []
    for i in range(months_back - 1, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        buckets.append((year, month))

    labels = [f"{m:02d}/{y}" for y, m in buckets]
    counts = []
    for year, month in buckets:
        count = Application.query.filter(
            func.extract("year", Application.submitted_at) == year,
            func.extract("month", Application.submitted_at) == month,
            Application.submitted_at.isnot(None),
        ).count()
        counts.append(count)

    return labels, counts


def get_faculty_stats():
    """Returns {faculty_name: application_count} for submitted+ applications."""
    rows = (
        db.session.query(Faculty.name, func.count(Application.id))
        .join(Department, Department.faculty_id == Faculty.id)
        .join(Programme, Programme.department_id == Department.id)
        .join(Application, Application.programme_id == Programme.id)
        .filter(Application.status != ApplicationStatus.DRAFT)
        .group_by(Faculty.name)
        .all()
    )
    return {name: count for name, count in rows}


# --- Applicant search / filtering ---

def search_applications(*, search_term=None, status=None, faculty_id=None,
                         department_id=None, programme_id=None, session_id=None,
                         page=1, per_page=20):
    query = (
        Application.query.join(ApplicantProfile)
        .join(User, ApplicantProfile.user_id == User.id)
        .join(Programme, Application.programme_id == Programme.id)
        .join(Department, Programme.department_id == Department.id)
        .join(Faculty, Department.faculty_id == Faculty.id)
        .filter(Application.status != ApplicationStatus.DRAFT)
    )

    if search_term:
        like = f"%{search_term}%"
        query = query.filter(
            or_(
                ApplicantProfile.first_name.ilike(like),
                ApplicantProfile.last_name.ilike(like),
                User.email.ilike(like),
                Application.application_number.ilike(like),
                Application.utme_registration_number.ilike(like),
            )
        )

    if status:
        query = query.filter(Application.status == status)
    if faculty_id:
        query = query.filter(Faculty.id == faculty_id)
    if department_id:
        query = query.filter(Department.id == department_id)
    if programme_id:
        query = query.filter(Programme.id == programme_id)
    if session_id:
        query = query.filter(Application.academic_session_id == session_id)

    query = query.order_by(Application.submitted_at.desc())
    return query.paginate(page=page, per_page=per_page, error_out=False)


# --- Decisions ---

def approve_application(application: Application, decided_by: User, remarks: str = None):
    from app.services.admission_letter_service import issue_admission_letter

    decision = AdmissionDecision(
        application_id=application.id,
        decided_by_id=decided_by.id,
        status=DecisionStatus.APPROVED,
        remarks=remarks,
    )
    db.session.add(decision)
    application.status = ApplicationStatus.APPROVED
    db.session.commit()

    issue_admission_letter(decision)

    _notify_applicant(
        application,
        title="Application Approved",
        message=(
            f"Congratulations! Your application ({application.application_number}) for "
            f"{application.programme.name} has been approved. Your admission letter with "
            "a scannable QR code is now available."
        ),
        notification_type=NotificationType.SUCCESS,
    )
    return decision


def reject_application(application: Application, decided_by: User, remarks: str = None):
    decision = AdmissionDecision(
        application_id=application.id,
        decided_by_id=decided_by.id,
        status=DecisionStatus.REJECTED,
        remarks=remarks,
    )
    db.session.add(decision)
    application.status = ApplicationStatus.REJECTED
    db.session.commit()

    _notify_applicant(
        application,
        title="Application Decision",
        message=(
            f"We regret to inform you that your application ({application.application_number}) "
            "was not successful this admission cycle."
        ),
        notification_type=NotificationType.WARNING,
    )
    return decision


def mark_under_review(application: Application):
    application.status = ApplicationStatus.UNDER_REVIEW
    db.session.commit()


def _notify_applicant(application, *, title, message, notification_type):
    user_id = application.applicant.user_id
    notification = Notification(
        recipient_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
    )
    db.session.add(notification)
    db.session.commit()
