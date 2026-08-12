"""
Custom Flask CLI commands.

Usage:
    flask seed-roles
    flask create-super-admin
    flask seed-demo-data
"""

import click
from app.extensions import db


def register_cli_commands(app):

    @app.cli.command("seed-roles")
    def seed_roles():
        """Create the default roles if they don't already exist."""
        from app.models import Role

        default_roles = [
            ("applicant", "Prospective student applying for admission"),
            ("admin", "Admissions officer with management access"),
            ("super_admin", "Full system access including user & settings management"),
            ("registrar", "Registrar with read access to reports and admission letters"),
        ]
        created = 0
        for name, description in default_roles:
            if not Role.query.filter_by(name=name).first():
                db.session.add(Role(name=name, description=description))
                created += 1
        db.session.commit()
        click.echo(f"Seeded roles. {created} new role(s) created.")

    @app.cli.command("create-super-admin")
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_super_admin(email, password):
        """Create the first super_admin account."""
        from app.models import User, Role

        role = Role.query.filter_by(name="super_admin").first()
        if not role:
            click.echo("super_admin role not found. Run `flask seed-roles` first.")
            return

        if User.query.filter_by(email=email).first():
            click.echo("A user with that email already exists.")
            return

        user = User(email=email, role=role, is_active=True, is_verified=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Super admin account created for {email}.")

    @app.cli.command("seed-academic-structure")
    def seed_academic_structure():
        """Seed a minimal set of faculties/departments/programmes/sessions for demo purposes."""
        from app.models import Faculty, Department, Programme, AcademicSession

        if not AcademicSession.query.filter_by(name=app.config["CURRENT_ACADEMIC_SESSION"]).first():
            db.session.add(
                AcademicSession(name=app.config["CURRENT_ACADEMIC_SESSION"], is_current=True)
            )

        if not Faculty.query.filter_by(code="SCI").first():
            faculty = Faculty(name="Faculty of Science", code="SCI")
            db.session.add(faculty)
            db.session.flush()

            dept = Department(name="Department of Computer Science", code="CSC", faculty_id=faculty.id)
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

        db.session.commit()
        click.echo("Academic structure seeded.")
