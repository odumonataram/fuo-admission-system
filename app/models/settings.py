"""
SystemSetting: simple key/value store for settings an admin can change at
runtime without redeploying (e.g. toggling application intake on/off).
"""

from app.extensions import db
from app.models.base import TimestampMixin


class SystemSetting(db.Model, TimestampMixin):
    __tablename__ = "system_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(255))

    def __repr__(self):
        return f"<SystemSetting {self.key}={self.value}>"
