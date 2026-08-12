"""
Application factory for the Federal University Otuoke
Computerized Student Admission System.
"""

import os
from flask import Flask, render_template

from config import config
from app.extensions import db, migrate, login_manager, csrf, mail, limiter


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__, instance_relative_config=True)

    # Ensure Flask's instance directory exists before SQLite is opened.
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    _ensure_upload_directories(app)
    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_cli_commands(app)
    _register_context_processors(app)
    _seed_default_data(app)

    return app


def _ensure_upload_directories(app):
    base = app.config["UPLOAD_FOLDER"]

    subdirs = [
        app.config["PASSPORT_UPLOAD_SUBDIR"],
        app.config["DOCUMENT_UPLOAD_SUBDIR"],
        app.config["QRCODE_SUBDIR"],
        app.config["ADMISSION_LETTER_SUBDIR"],
    ]

    os.makedirs(base, exist_ok=True)

    for sub in subdirs:
        os.makedirs(os.path.join(base, sub), exist_ok=True)


def _init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

    # Import models so Flask-Migrate can see them.
    with app.app_context():
        from app import models  # noqa: F401


def _register_blueprints(app):
    from app.blueprints.public.routes import public_bp
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.applicant.routes import applicant_bp
    from app.blueprints.administrator.routes import administrator_bp
    from app.blueprints.admission.routes import admission_bp
    from app.blueprints.verification.routes import verification_bp
    from app.blueprints.reports.routes import reports_bp
    from app.blueprints.settings.routes import settings_bp
    from app.blueprints.audit.routes import audit_bp
    from app.blueprints.notifications.routes import notifications_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(applicant_bp, url_prefix="/applicant")
    app.register_blueprint(administrator_bp, url_prefix="/admin")
    app.register_blueprint(admission_bp, url_prefix="/admin/admission")
    app.register_blueprint(verification_bp, url_prefix="/verify")
    app.register_blueprint(reports_bp, url_prefix="/admin/reports")
    app.register_blueprint(settings_bp, url_prefix="/admin/settings")
    app.register_blueprint(audit_bp, url_prefix="/admin/audit")
    app.register_blueprint(notifications_bp, url_prefix="/notifications")


def _register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("shared/errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("shared/errors/404.html"), 404

    @app.errorhandler(413)
    def file_too_large(e):
        return render_template("shared/errors/413.html"), 413

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("shared/errors/500.html"), 500


def _register_cli_commands(app):
    from app.utils.cli import register_cli_commands

    register_cli_commands(app)


def _seed_default_data(app):
    """
    Auto-create default roles and a default admin account on startup.

    This allows the application to work immediately after deployment
    without manually running database setup commands.
    """

    with app.app_context():
        from app.models import User, Role

        try:
            db.create_all()
        except Exception as e:
            app.logger.warning(
                f"Skipping default data seed — could not create tables: {e}"
            )
            return

        # ---------------------------------------------------------
        # Seed roles
        # ---------------------------------------------------------
        default_roles = [
            (
                "applicant",
                "Prospective student applying for admission",
            ),
            (
                "admin",
                "Admissions officer with management access",
            ),
            (
                "super_admin",
                "Full system access including user & settings management",
            ),
            (
                "registrar",
                "Registrar with read access to reports and admission letters",
            ),
        ]

        for name, description in default_roles:
            if not Role.query.filter_by(name=name).first():
                db.session.add(
                    Role(
                        name=name,
                        description=description,
                    )
                )

        db.session.commit()

        # ---------------------------------------------------------
        # Seed default administrator
        # ---------------------------------------------------------
        DEFAULT_ADMIN_EMAIL = "admin@fuo.edu.ng"
        DEFAULT_ADMIN_PASSWORD = "Admin@123"

        admin_role = Role.query.filter_by(
            name="super_admin"
        ).first()

        if (
            admin_role
            and not User.query.filter_by(
                email=DEFAULT_ADMIN_EMAIL
            ).first()
        ):
            default_admin = User(
                email=DEFAULT_ADMIN_EMAIL,
                role=admin_role,
                is_active=True,
                is_verified=True,
            )

            default_admin.set_password(DEFAULT_ADMIN_PASSWORD)

            db.session.add(default_admin)
            db.session.commit()

            app.logger.info(
                "Default admin created — "
                f"email: {DEFAULT_ADMIN_EMAIL}"
            )


def _register_context_processors(app):
    @app.context_processor
    def inject_globals():
        from datetime import datetime

        return {
            "current_year": datetime.utcnow().year,
            "app_name": "Federal University Otuoke Admission System",
            "university_short_name": "FUO",
        }