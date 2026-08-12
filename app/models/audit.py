"""
AuditLog: records security-relevant and administrative actions
(logins, approvals, rejections, settings changes, user management, etc.)
"""

from datetime import datetime
from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    action = db.Column(db.String(100), nullable=False, index=True)  # e.g. "APPROVE_APPLICATION"
    entity_type = db.Column(db.String(50))  # e.g. "Application"
    entity_id = db.Column(db.Integer)

    description = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    actor = db.relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.action} by user#{self.actor_id}>"
