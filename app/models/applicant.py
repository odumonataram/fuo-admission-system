"""
ApplicantProfile: biodata for a User with role='applicant'.

Kept separate from User so the `users` table stays lean for authentication,
and so staff accounts never carry applicant-only columns.
"""

from app.extensions import db
from app.models.base import TimestampMixin


class ApplicantProfile(db.Model, TimestampMixin):
    __tablename__ = "applicant_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    # Personal details
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    middle_name = db.Column(db.String(80))
    gender = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)
    nationality = db.Column(db.String(80), default="Nigerian")
    state_of_origin = db.Column(db.String(80))
    lga = db.Column(db.String(80))  # Local Government Area
    home_address = db.Column(db.Text)
    passport_photo_path = db.Column(db.String(255))  # relative path under UPLOAD_FOLDER

    # Guardian / next of kin
    guardian_name = db.Column(db.String(150))
    guardian_phone = db.Column(db.String(20))
    guardian_address = db.Column(db.Text)

    profile_completed = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship("User", back_populates="applicant_profile")
    applications = db.relationship(
        "Application", back_populates="applicant", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        parts = [self.last_name, self.first_name, self.middle_name]
        return " ".join(p for p in parts if p)

    def __repr__(self):
        return f"<ApplicantProfile {self.full_name}>"
