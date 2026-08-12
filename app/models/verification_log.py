"""
VerificationLog: an immutable audit record of every attempt to verify an
admission letter (whether the token was valid or not).
"""

from datetime import datetime
from app.extensions import db


class VerificationLog(db.Model):
    __tablename__ = "verification_logs"

    id = db.Column(db.Integer, primary_key=True)

    # Nullable because an invalid/unknown token still gets logged.
    token_id = db.Column(
        db.Integer, db.ForeignKey("verification_tokens.id"), nullable=True
    )

    token_value_attempted = db.Column(db.String(36), nullable=False)
    result = db.Column(db.String(20), nullable=False)  # "valid" or "invalid"

    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    verified_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    token = db.relationship("VerificationToken", back_populates="verification_logs")

    def __repr__(self):
        return f"<VerificationLog {self.token_value_attempted} - {self.result}>"
