"""
Simple local development entry point.

Just run:
python app.py

This script automatically:

- creates a .env file from .env.example if one doesn't exist yet
  (with a random SECRET_KEY generated for you)
- creates the SQLite database and all tables if they don't exist
- seeds default roles (applicant, admin, super_admin, registrar)
- seeds a starter faculty/department/programme so the site isn't empty
- starts the Flask development server

For production deployment, use wsgi.py with gunicorn instead — that
path expects a properly configured .env and MySQL, and does NOT
auto-seed anything.
"""

import os
import secrets
import shutil


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
ENV_EXAMPLE_PATH = os.path.join(BASE_DIR, ".env.example")


def ensure_env_file():
    """Create .env from .env.example on first run, with a real secret key."""
    if os.path.exists(ENV_PATH):
        return

    shutil.copy(ENV_EXAMPLE_PATH, ENV_PATH)

    generated_key = secrets.token_hex(32)

    with open(ENV_PATH, "r") as f:
        content = f.read()

    content = content.replace(
        "SECRET_KEY=change-this-to-a-random-64-character-string",
        f"SECRET_KEY={generated_key}",
    )

    with open(ENV_PATH, "w") as f:
        f.write(content)

    print(">> Created .env file with a generated SECRET_KEY (first run).")


def seed_defaults(app):
    from app.extensions import db
    from app.models import (
        Role,
        Faculty,
        Department,
        Programme,
        AcademicSession,
    )

    with app.app_context():
        db.create_all()

        if Role.query.count() == 0:
            for name, description in [
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
            ]:
                db.session.add(
                    Role(
                        name=name,
                        description=description,
                    )
                )

            print(">> Seeded default roles.")

        session_name = app.config["CURRENT_ACADEMIC_SESSION"]

        if not AcademicSession.query.filter_by(name=session_name).first():
            db.session.add(
                AcademicSession(
                    name=session_name,
                    is_current=True,
                )
            )

            print(f">> Seeded academic session {session_name}.")

        if Faculty.query.count() == 0:
            faculty = Faculty(
                name="Faculty of Science",
                code="SCI",
            )

            db.session.add(faculty)
            db.session.flush()

            dept = Department(
                name="Department of Computer Science",
                code="CSC",
                faculty_id=faculty.id,
            )

            db.session.add(dept)
            db.session.flush()

            db.session.add(
                Programme(
                    name="Computer Science",
                    code="CSC-BSC",
                    department_id=dept.id,
                    degree_type="B.Sc.",
                    duration_years=4,
                    admission_capacity=150,
                )
            )

            print(">> Seeded a starter faculty/department/programme.")

        db.session.commit()


if __name__ == "__main__":
    ensure_env_file()

    from app import create_app

    app = create_app(
        os.environ.get("FLASK_ENV", "development")
    )

    seed_defaults(app)

    print("\n" + "=" * 60)
    print(" Federal University Otuoke Admission System")
    print(" Running locally at: http://127.0.0.1:5000")
    print(" Phone access:      http://192.168.1.34:5000")
    print("=" * 60 + "\n")

    # 0.0.0.0 allows other devices on the same network,
    # such as your phone, to access the Flask application.
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )