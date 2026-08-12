"""
Applicant forms: profile editing, the main application form (programme
selection + UTME + O'Level details), and document uploads.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import (
    StringField,
    SelectField,
    IntegerField,
    DateField,
    TextAreaField,
    FieldList,
    FormField,
    SubmitField,
)
from wtforms.validators import DataRequired, Length, Optional, NumberRange, ValidationError

GENDER_CHOICES = [("", "Select gender"), ("Male", "Male"), ("Female", "Female")]

OLEVEL_EXAM_CHOICES = [
    ("", "Select exam type"),
    ("WAEC", "WAEC"),
    ("NECO", "NECO"),
    ("NABTEB", "NABTEB"),
]

GRADE_CHOICES = [
    ("", "-"),
    ("A1", "A1"), ("B2", "B2"), ("B3", "B3"),
    ("C4", "C4"), ("C5", "C5"), ("C6", "C6"),
    ("D7", "D7"), ("E8", "E8"), ("F9", "F9"),
]

IMAGE_ALLOWED_MSG = "Only JPG and PNG images are allowed."
DOC_ALLOWED_MSG = "Only PDF, JPG, or PNG files are allowed."
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB, mirrors MAX_CONTENT_LENGTH


class ProfileForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=80)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=80)])
    middle_name = StringField("Middle Name", validators=[Optional(), Length(max=80)])
    gender = SelectField("Gender", choices=GENDER_CHOICES, validators=[DataRequired()])
    date_of_birth = DateField("Date of Birth", validators=[DataRequired()], format="%Y-%m-%d")
    nationality = StringField("Nationality", validators=[DataRequired(), Length(max=80)])
    state_of_origin = StringField("State of Origin", validators=[DataRequired(), Length(max=80)])
    lga = StringField("Local Government Area", validators=[DataRequired(), Length(max=80)])
    home_address = TextAreaField("Home Address", validators=[DataRequired(), Length(max=500)])

    guardian_name = StringField("Guardian/Next of Kin Name", validators=[DataRequired(), Length(max=150)])
    guardian_phone = StringField("Guardian Phone Number", validators=[DataRequired(), Length(max=20)])
    guardian_address = TextAreaField("Guardian Address", validators=[Optional(), Length(max=500)])

    passport_photo = FileField(
        "Passport Photograph",
        validators=[
            Optional(),
            FileAllowed(["jpg", "jpeg", "png"], IMAGE_ALLOWED_MSG),
            FileSize(max_size=MAX_FILE_SIZE_BYTES, message="File must be under 5 MB."),
        ],
    )
    submit = SubmitField("Save Profile")


class ProgrammeSelectionForm(FlaskForm):
    faculty_id = SelectField("Faculty", coerce=int, validators=[DataRequired()])
    department_id = SelectField("Department", coerce=int, validators=[DataRequired()])
    programme_id = SelectField("Programme", coerce=int, validators=[DataRequired()])


class UTMESubjectEntry(FlaskForm):
    """One row of a UTME subject + score. Disable CSRF since it's a sub-form."""
    class Meta:
        csrf = False

    subject = StringField("Subject", validators=[Optional(), Length(max=80)])
    score = IntegerField("Score", validators=[Optional(), NumberRange(min=0, max=100)])


class OLevelResultEntry(FlaskForm):
    class Meta:
        csrf = False

    subject = StringField("Subject", validators=[Optional(), Length(max=80)])
    grade = SelectField("Grade", choices=GRADE_CHOICES, validators=[Optional()])


class ApplicationForm(FlaskForm):
    faculty_id = SelectField("Faculty", coerce=int, validators=[DataRequired()])
    department_id = SelectField("Department", coerce=int, validators=[DataRequired()])
    programme_id = SelectField("Programme", coerce=int, validators=[DataRequired()])

    utme_registration_number = StringField(
        "UTME Registration Number", validators=[DataRequired(), Length(max=30)]
    )
    utme_score = IntegerField(
        "UTME Score", validators=[DataRequired(), NumberRange(min=0, max=400)]
    )
    utme_subjects = FieldList(FormField(UTMESubjectEntry), min_entries=4, max_entries=4)

    olevel_exam_type = SelectField(
        "Examination Type", choices=OLEVEL_EXAM_CHOICES, validators=[DataRequired()]
    )
    olevel_exam_year = IntegerField(
        "Examination Year", validators=[DataRequired(), NumberRange(min=1990, max=2100)]
    )
    olevel_results = FieldList(FormField(OLevelResultEntry), min_entries=9, max_entries=9)

    submit = SubmitField("Save Application Details")

    def validate_olevel_results(self, field):
        filled = [
            entry for entry in field.entries
            if entry.form.subject.data and entry.form.grade.data
        ]
        if len(filled) < 5:
            raise ValidationError("Provide at least 5 O'Level subjects with grades.")

        subjects_lower = [entry.form.subject.data.strip().lower() for entry in filled]
        if "english language" not in subjects_lower and "english" not in subjects_lower:
            raise ValidationError("English Language is a required O'Level subject.")
        if "mathematics" not in subjects_lower:
            raise ValidationError("Mathematics is a required O'Level subject.")

        credit_grades = {"A1", "B2", "B3", "C4", "C5", "C6"}
        non_credit = [
            entry.form.subject.data for entry in filled
            if entry.form.grade.data not in credit_grades
        ]
        if non_credit:
            raise ValidationError(
                f"These subjects do not have a credit-level grade (A1-C6): {', '.join(non_credit)}"
            )

    def validate_utme_subjects(self, field):
        filled = [entry for entry in field.entries if entry.form.subject.data]
        if len(filled) < 4:
            raise ValidationError("All 4 UTME subjects (including English Language) are required.")
        subjects_lower = [entry.form.subject.data.strip().lower() for entry in filled]
        if "english language" not in subjects_lower and "english" not in subjects_lower:
            raise ValidationError("English Language is a required UTME subject.")


class DocumentUploadForm(FlaskForm):
    olevel_result = FileField(
        "O'Level Result",
        validators=[
            Optional(),
            FileAllowed(["pdf", "jpg", "jpeg", "png"], DOC_ALLOWED_MSG),
            FileSize(max_size=MAX_FILE_SIZE_BYTES, message="File must be under 5 MB."),
        ],
    )
    utme_result_slip = FileField(
        "UTME Result Slip",
        validators=[
            Optional(),
            FileAllowed(["pdf", "jpg", "jpeg", "png"], DOC_ALLOWED_MSG),
            FileSize(max_size=MAX_FILE_SIZE_BYTES, message="File must be under 5 MB."),
        ],
    )
    birth_certificate = FileField(
        "Birth Certificate / Age Declaration",
        validators=[
            Optional(),
            FileAllowed(["pdf", "jpg", "jpeg", "png"], DOC_ALLOWED_MSG),
            FileSize(max_size=MAX_FILE_SIZE_BYTES, message="File must be under 5 MB."),
        ],
    )
    lga_certificate = FileField(
        "LGA Certificate of Origin (optional)",
        validators=[
            Optional(),
            FileAllowed(["pdf", "jpg", "jpeg", "png"], DOC_ALLOWED_MSG),
            FileSize(max_size=MAX_FILE_SIZE_BYTES, message="File must be under 5 MB."),
        ],
    )
    submit = SubmitField("Upload Documents")
