"""
Academic service: small CRUD helpers for Faculty, Department, Programme,
and AcademicSession used by the administrator blueprint.
"""

from app.extensions import db
from app.models import AcademicSession


def set_current_session(session_id):
    """Ensure exactly one AcademicSession has is_current=True."""
    AcademicSession.query.update({AcademicSession.is_current: False})
    session = AcademicSession.query.get(session_id)
    if session:
        session.is_current = True
    db.session.commit()
    return session


def toggle_active(model_class, record_id):
    record = model_class.query.get(record_id)
    if record:
        record.is_active = not record.is_active
        db.session.commit()
    return record
