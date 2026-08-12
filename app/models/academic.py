"""
Academic structure models: Faculty -> Department -> Programme,
plus AcademicSession (e.g. "2025/2026") which every application belongs to.
"""

from app.extensions import db
from app.models.base import TimestampMixin


class Faculty(db.Model, TimestampMixin):
    __tablename__ = "faculties"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    departments = db.relationship(
        "Department", back_populates="faculty", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Faculty {self.code}>"


class Department(db.Model, TimestampMixin):
    __tablename__ = "departments"
    __table_args__ = (
        db.UniqueConstraint("faculty_id", "name", name="uq_department_per_faculty"),
    )

    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculties.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    faculty = db.relationship("Faculty", back_populates="departments")
    programmes = db.relationship(
        "Programme", back_populates="department", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Department {self.code}>"


class Programme(db.Model, TimestampMixin):
    __tablename__ = "programmes"

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    degree_type = db.Column(db.String(50), default="B.Sc.", nullable=False)
    duration_years = db.Column(db.Integer, default=4, nullable=False)
    admission_capacity = db.Column(db.Integer, default=100, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    department = db.relationship("Department", back_populates="programmes")
    applications = db.relationship("Application", back_populates="programme")

    def __repr__(self):
        return f"<Programme {self.code}>"


class AcademicSession(db.Model, TimestampMixin):
    """e.g. '2025/2026'. Only one session should be flagged is_current at a time."""

    __tablename__ = "academic_sessions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)  # "2025/2026"
    is_current = db.Column(db.Boolean, default=False, nullable=False)
    application_open_date = db.Column(db.Date, nullable=True)
    application_close_date = db.Column(db.Date, nullable=True)

    applications = db.relationship("Application", back_populates="academic_session")

    def __repr__(self):
        return f"<AcademicSession {self.name}>"
