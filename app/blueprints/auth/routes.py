"""
Auth blueprint: registration, login, logout, forgot/reset password,
change password. All state-changing routes are CSRF protected via
Flask-WTF forms, and rate-limited on the sensitive endpoints.
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user,
)

from app.extensions import db, limiter
from app.blueprints.auth.forms import (
    RegistrationForm,
    LoginForm,
    ForgotPasswordForm,
    ResetPasswordForm,
    ChangePasswordForm,
)
from app.services import auth_service
from app.services.email_service import send_password_reset_email, send_welcome_email

auth_bp = Blueprint("auth", __name__)


def _redirect_after_login(user):
    if user.is_admin:
        return redirect(url_for("administrator.dashboard"))
    return redirect(url_for("applicant.dashboard"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return _redirect_after_login(current_user)

    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = auth_service.register_applicant(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                email=form.email.data,
                phone_number=form.phone_number.data,
                password=form.password.data,
            )
        except RuntimeError as exc:
            flash(str(exc), "error")
            return render_template("auth/register.html", form=form)

        send_welcome_email(user)
        auth_service.log_action(
            actor_id=user.id,
            action="USER_REGISTERED",
            entity_type="User",
            entity_id=user.id,
            description=f"New applicant account registered: {user.email}",
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
        )
        flash("Account created successfully! Please log in to continue.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return _redirect_after_login(current_user)

    form = LoginForm()
    if form.validate_on_submit():
        user, error = auth_service.authenticate(form.email.data, form.password.data)

        if error:
            flash(error, "error")
            return render_template("auth/login.html", form=form)

        user.register_successful_login(ip_address=request.remote_addr)
        db.session.commit()

        login_user(user, remember=form.remember_me.data)
        auth_service.log_action(
            actor_id=user.id,
            action="USER_LOGIN",
            entity_type="User",
            entity_id=user.id,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
        )

        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        return _redirect_after_login(user)

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    auth_service.log_action(
        actor_id=current_user.id,
        action="USER_LOGOUT",
        entity_type="User",
        entity_id=current_user.id,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
    )
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("public.home"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        from app.models import User

        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        # Always show the same message, whether or not the account exists,
        # to avoid leaking which emails are registered.
        if user:
            token = auth_service.generate_password_reset_token(user)
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            send_password_reset_email(user, reset_url)

        flash(
            "If an account exists with that email, a password reset link has been sent.",
            "info",
        )
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = auth_service.verify_password_reset_token(token)
    if not user:
        flash("This password reset link is invalid or has expired.", "error")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        auth_service.complete_password_reset(user, form.password.data)
        auth_service.log_action(
            actor_id=user.id,
            action="PASSWORD_RESET",
            entity_type="User",
            entity_id=user.id,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
        )
        flash("Your password has been reset. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form, token=token)


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "error")
            return render_template("auth/change_password.html", form=form)

        current_user.set_password(form.new_password.data)
        db.session.commit()
        auth_service.log_action(
            actor_id=current_user.id,
            action="PASSWORD_CHANGED",
            entity_type="User",
            entity_id=current_user.id,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
        )
        flash("Your password has been changed successfully.", "success")
        return _redirect_after_login(current_user)

    return render_template("auth/change_password.html", form=form)
