"""
Auth forms: registration, login, forgot password, reset password,
change password. All server-side validated via WTForms validators
(never trust client-side validation alone).
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    Regexp,
    ValidationError,
)

from app.models import User


PASSWORD_MIN_LENGTH = 8
PASSWORD_REGEX = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$"
PASSWORD_MESSAGE = (
    "Password must be at least 8 characters and include an uppercase letter, "
    "a lowercase letter, and a number."
)


class RegistrationForm(FlaskForm):
    first_name = StringField(
        "First Name", validators=[DataRequired(), Length(max=80)]
    )
    last_name = StringField(
        "Last Name", validators=[DataRequired(), Length(max=80)]
    )
    email = StringField(
        "Email Address", validators=[DataRequired(), Email(), Length(max=120)]
    )
    phone_number = StringField(
        "Phone Number",
        validators=[
            DataRequired(),
            Regexp(r"^\+?[0-9]{10,15}$", message="Enter a valid phone number."),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=PASSWORD_MIN_LENGTH, message=PASSWORD_MESSAGE),
            Regexp(PASSWORD_REGEX, message=PASSWORD_MESSAGE),
        ],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords do not match."),
        ],
    )
    agree_terms = BooleanField(
        "I confirm the information I provide is accurate",
        validators=[DataRequired(message="You must confirm this to continue.")],
    )
    submit = SubmitField("Create Account")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError("An account with this email already exists.")

    def validate_phone_number(self, field):
        if User.query.filter_by(phone_number=field.data.strip()).first():
            raise ValidationError("An account with this phone number already exists.")


class LoginForm(FlaskForm):
    email = StringField("Email Address", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember me")
    submit = SubmitField("Login")


class ForgotPasswordForm(FlaskForm):
    email = StringField("Email Address", validators=[DataRequired(), Email()])
    submit = SubmitField("Send Reset Link")


class ResetPasswordForm(FlaskForm):
    password = PasswordField(
        "New Password",
        validators=[
            DataRequired(),
            Length(min=PASSWORD_MIN_LENGTH, message=PASSWORD_MESSAGE),
            Regexp(PASSWORD_REGEX, message=PASSWORD_MESSAGE),
        ],
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords do not match."),
        ],
    )
    submit = SubmitField("Reset Password")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField(
        "New Password",
        validators=[
            DataRequired(),
            Length(min=PASSWORD_MIN_LENGTH, message=PASSWORD_MESSAGE),
            Regexp(PASSWORD_REGEX, message=PASSWORD_MESSAGE),
        ],
    )
    confirm_new_password = PasswordField(
        "Confirm New Password",
        validators=[
            DataRequired(),
            EqualTo("new_password", message="Passwords do not match."),
        ],
    )
    submit = SubmitField("Change Password")
