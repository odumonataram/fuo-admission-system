"""
Administrator blueprint: dashboard, manage applicants (search/filter/
approve/reject), manage faculties/departments/programmes/sessions,
manage staff accounts.
"""

import json

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models import (
    Faculty,
    Department,
    Programme,
    AcademicSession,
    Application,
    User,
    Role,
)
from app.models.application import ApplicationStatus
from app.utils.decorators import roles_required
from app.services import admin_service, academic_service, auth_service
from app.blueprints.administrator.forms import (
    FacultyForm,
    DepartmentForm,
    ProgrammeForm,
    AcademicSessionForm,
    DecisionForm,
    StaffAccountForm,
)

administrator_bp = Blueprint("administrator", __name__)


# --- Dashboard ---

@administrator_bp.route("/dashboard")
@login_required
@roles_required("admin", "super_admin", "registrar")
def dashboard():
    stats = admin_service.get_dashboard_stats()
    month_labels, month_counts = admin_service.get_monthly_application_counts()
    faculty_stats = admin_service.get_faculty_stats()

    return render_template(
        "administrator/dashboard.html",
        stats=stats,
        month_labels=json.dumps(month_labels),
        month_counts=json.dumps(month_counts),
        faculty_labels=json.dumps(list(faculty_stats.keys())),
        faculty_counts=json.dumps(list(faculty_stats.values())),
    )


# --- Manage applicants ---

@administrator_bp.route("/applicants")
@login_required
@roles_required("admin", "super_admin", "registrar")
def applicants_list():
    page = request.args.get("page", 1, type=int)
    search_term = request.args.get("q", "").strip() or None
    status = request.args.get("status") or None
    faculty_id = request.args.get("faculty_id", type=int) or None
    session_id = request.args.get("session_id", type=int) or None

    pagination = admin_service.search_applications(
        search_term=search_term,
        status=status,
        faculty_id=faculty_id,
        session_id=session_id,
        page=page,
    )

    faculties = Faculty.query.filter_by(is_active=True).order_by(Faculty.name).all()
    sessions = AcademicSession.query.order_by(AcademicSession.name.desc()).all()

    return render_template(
        "administrator/applicants_list.html",
        pagination=pagination,
        applications=pagination.items,
        faculties=faculties,
        sessions=sessions,
        filters={
            "q": search_term or "",
            "status": status or "",
            "faculty_id": faculty_id or "",
            "session_id": session_id or "",
        },
        statuses=ApplicationStatus.CHOICES,
    )


@administrator_bp.route("/applicants/<int:application_id>", methods=["GET", "POST"])
@login_required
@roles_required("admin", "super_admin", "registrar")
def applicant_detail(application_id):
    application = Application.query.get_or_404(application_id)
    profile = application.applicant

    form = DecisionForm()
    can_decide = current_user.has_role("admin", "super_admin") and application.status in (
        ApplicationStatus.SUBMITTED, ApplicationStatus.UNDER_REVIEW
    )

    if can_decide and form.validate_on_submit():
        if form.submit_approve.data:
            admin_service.approve_application(application, current_user, form.remarks.data)
            auth_service.log_action(
                actor_id=current_user.id,
                action="APPLICATION_APPROVED",
                entity_type="Application",
                entity_id=application.id,
                description=f"Approved {application.application_number}",
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string,
            )
            flash(f"Application {application.application_number} approved.", "success")
        elif form.submit_reject.data:
            admin_service.reject_application(application, current_user, form.remarks.data)
            auth_service.log_action(
                actor_id=current_user.id,
                action="APPLICATION_REJECTED",
                entity_type="Application",
                entity_id=application.id,
                description=f"Rejected {application.application_number}",
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string,
            )
            flash(f"Application {application.application_number} rejected.", "info")
        return redirect(url_for("administrator.applicant_detail", application_id=application.id))

    # Auto-transition submitted -> under_review the first time an officer opens it.
    if application.status == ApplicationStatus.SUBMITTED and current_user.has_role("admin", "super_admin"):
        admin_service.mark_under_review(application)

    utme_subjects = json.loads(application.utme_subjects_json) if application.utme_subjects_json else []
    olevel_results = json.loads(application.olevel_results_json) if application.olevel_results_json else []
    documents = {doc.document_type: doc for doc in application.documents}

    return render_template(
        "administrator/applicant_detail.html",
        application=application,
        profile=profile,
        form=form,
        can_decide=can_decide,
        utme_subjects=utme_subjects,
        olevel_results=olevel_results,
        documents=documents,
    )


# --- Manage faculties ---

@administrator_bp.route("/faculties", methods=["GET", "POST"])
@login_required
@roles_required("admin", "super_admin")
def faculties():
    form = FacultyForm()
    if form.validate_on_submit():
        db.session.add(Faculty(
            name=form.name.data, code=form.code.data.upper(),
            description=form.description.data, is_active=form.is_active.data,
        ))
        db.session.commit()
        flash("Faculty created.", "success")
        return redirect(url_for("administrator.faculties"))

    all_faculties = Faculty.query.order_by(Faculty.name).all()
    return render_template("administrator/faculties.html", form=form, faculties=all_faculties)


@administrator_bp.route("/faculties/<int:faculty_id>/toggle")
@login_required
@roles_required("admin", "super_admin")
def toggle_faculty(faculty_id):
    academic_service.toggle_active(Faculty, faculty_id)
    return redirect(url_for("administrator.faculties"))


# --- Manage departments ---

@administrator_bp.route("/departments", methods=["GET", "POST"])
@login_required
@roles_required("admin", "super_admin")
def departments():
    form = DepartmentForm()
    form.faculty_id.choices = [(f.id, f.name) for f in Faculty.query.order_by(Faculty.name)]

    if form.validate_on_submit():
        db.session.add(Department(
            faculty_id=form.faculty_id.data, name=form.name.data,
            code=form.code.data.upper(), is_active=form.is_active.data,
        ))
        db.session.commit()
        flash("Department created.", "success")
        return redirect(url_for("administrator.departments"))

    all_departments = Department.query.order_by(Department.name).all()
    return render_template("administrator/departments.html", form=form, departments=all_departments)


@administrator_bp.route("/departments/<int:department_id>/toggle")
@login_required
@roles_required("admin", "super_admin")
def toggle_department(department_id):
    academic_service.toggle_active(Department, department_id)
    return redirect(url_for("administrator.departments"))


# --- Manage programmes ---

@administrator_bp.route("/programmes", methods=["GET", "POST"])
@login_required
@roles_required("admin", "super_admin")
def programmes():
    form = ProgrammeForm()
    form.department_id.choices = [(d.id, d.name) for d in Department.query.order_by(Department.name)]

    if form.validate_on_submit():
        db.session.add(Programme(
            department_id=form.department_id.data, name=form.name.data,
            code=form.code.data.upper(), degree_type=form.degree_type.data,
            duration_years=form.duration_years.data,
            admission_capacity=form.admission_capacity.data,
            is_active=form.is_active.data,
        ))
        db.session.commit()
        flash("Programme created.", "success")
        return redirect(url_for("administrator.programmes"))

    all_programmes = Programme.query.order_by(Programme.name).all()
    return render_template("administrator/programmes.html", form=form, programmes=all_programmes)


@administrator_bp.route("/programmes/<int:programme_id>/toggle")
@login_required
@roles_required("admin", "super_admin")
def toggle_programme(programme_id):
    academic_service.toggle_active(Programme, programme_id)
    return redirect(url_for("administrator.programmes"))


# --- Manage academic sessions ---

@administrator_bp.route("/sessions", methods=["GET", "POST"])
@login_required
@roles_required("admin", "super_admin")
def sessions():
    form = AcademicSessionForm()

    if form.validate_on_submit():
        new_session = AcademicSession(
            name=form.name.data,
            application_open_date=form.application_open_date.data,
            application_close_date=form.application_close_date.data,
        )
        db.session.add(new_session)
        db.session.commit()

        if form.is_current.data:
            academic_service.set_current_session(new_session.id)

        flash("Academic session created.", "success")
        return redirect(url_for("administrator.sessions"))

    all_sessions = AcademicSession.query.order_by(AcademicSession.name.desc()).all()
    return render_template("administrator/sessions.html", form=form, sessions=all_sessions)


@administrator_bp.route("/sessions/<int:session_id>/set-current")
@login_required
@roles_required("admin", "super_admin")
def set_current_session(session_id):
    academic_service.set_current_session(session_id)
    flash("Current academic session updated.", "success")
    return redirect(url_for("administrator.sessions"))


# --- Manage staff/users ---

@administrator_bp.route("/users", methods=["GET", "POST"])
@login_required
@roles_required("super_admin")
def users():
    form = StaffAccountForm()

    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower().strip()).first():
            flash("A user with that email already exists.", "error")
        else:
            role = Role.query.filter_by(name=form.role.data).first()
            if not role:
                flash("Selected role does not exist. Run `flask seed-roles`.", "error")
                return render_template("administrator/users.html", form=form, staff=_staff_list())

            user = User(
                email=form.email.data.lower().strip(),
                phone_number=form.phone_number.data.strip(),
                role=role,
                is_active=True,
                is_verified=True,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()

            auth_service.log_action(
                actor_id=current_user.id,
                action="STAFF_ACCOUNT_CREATED",
                entity_type="User",
                entity_id=user.id,
                description=f"Created {role.name} account for {user.email}",
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string,
            )
            flash(f"Staff account created for {user.email}.", "success")
            return redirect(url_for("administrator.users"))

    return render_template("administrator/users.html", form=form, staff=_staff_list())


def _staff_list():
    return (
        User.query.join(Role)
        .filter(Role.name.in_(["admin", "super_admin", "registrar"]))
        .order_by(User.created_at.desc())
        .all()
    )


@administrator_bp.route("/users/<int:user_id>/toggle")
@login_required
@roles_required("super_admin")
def toggle_user(user_id):
    if user_id == current_user.id:
        flash("You cannot deactivate your own account.", "error")
        return redirect(url_for("administrator.users"))

    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    flash(f"{user.email} has been {'activated' if user.is_active else 'deactivated'}.", "success")
    return redirect(url_for("administrator.users"))
