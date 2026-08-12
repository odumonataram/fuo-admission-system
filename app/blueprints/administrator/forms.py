"""
Administrator forms: faculty/department/programme/session CRUD,
admission decisions, and staff account creation.
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    IntegerField,
    SelectField,
    TextAreaField,
    DateField,
    BooleanField,
    SubmitField,
    PasswordField,
)
from wtforms.validators import DataRequired, Length, Optional, NumberRange, Email, EqualTo, Regexp

from app.blueprints.auth.forms import PASSWORD_MIN_LENGTH, PASSWORD_REGEX, PASSWORD_MESSAGE


class FacultyForm(FlaskForm):
    name = StringField("Faculty Name", validators=[DataRequired(), Length(max=150)])
    code = StringField("Code", validators=[DataRequired(), Length(max=20)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=1000)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Faculty")


class DepartmentForm(FlaskForm):
    faculty_id = SelectField("Faculty", coerce=int, validators=[DataRequired()])
    name = StringField("Department Name", validators=[DataRequired(), Length(max=150)])
    code = StringField("Code", validators=[DataRequired(), Length(max=20)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Department")


class ProgrammeForm(FlaskForm):
    department_id = SelectField("Department", coerce=int, validators=[DataRequired()])
    name = StringField("Programme Name", validators=[DataRequired(), Length(max=150)])
    code = StringField("Code", validators=[DataRequired(), Length(max=20)])
    degree_type = SelectField(
        "Degree Type",
        choices=[("B.Sc.", "B.Sc."), ("B.A.", "B.A."), ("B.Eng.", "B.Eng."), ("LL.B.", "LL.B.")],
        validators=[DataRequired()],
    )
    duration_years = IntegerField("Duration (Years)", validators=[DataRequired(), NumberRange(min=1, max=10)])
    admission_capacity = IntegerField("Admission Capacity", validators=[DataRequired(), NumberRange(min=1)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Programme")


class AcademicSessionForm(FlaskForm):
    name = StringField("Session Name (e.g. 2025/2026)", validators=[DataRequired(), Length(max=20)])
    application_open_date = DateField("Application Open Date", validators=[Optional()], format="%Y-%m-%d")
    application_close_date = DateField("Application Close Date", validators=[Optional()], format="%Y-%m-%d")
    is_current = BooleanField("Set as Current Session")
    submit = SubmitField("Save Session")


class DecisionForm(FlaskForm):
    remarks = TextAreaField("Remarks (optional)", validators=[Optional(), Length(max=1000)])
    submit_approve = SubmitField("Approve")
    submit_reject = SubmitField("Reject")


class StaffAccountForm(FlaskForm):
    email = StringField("Email Address", validators=[DataRequired(), Email(), Length(max=120)])
    phone_number = StringField("Phone Number", validators=[DataRequired(), Length(max=20)])
    role = SelectField(
        "Role",
        choices=[("admin", "Admissions Officer"), ("registrar", "Registrar"), ("super_admin", "Super Admin")],
        validators=[DataRequired()],
    )
    password = PasswordField(
        "Temporary Password",
        validators=[
            DataRequired(),
            Length(min=PASSWORD_MIN_LENGTH, message=PASSWORD_MESSAGE),
            Regexp(PASSWORD_REGEX, message=PASSWORD_MESSAGE),
        ],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords do not match.")],
    )
    submit = SubmitField("Create Staff Account")
