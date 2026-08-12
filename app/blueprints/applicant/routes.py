"""
Applicant blueprint: dashboard, profile management, the main application
form (programme + UTME + O'Level), document uploads, preview, submission,
and status tracking.
"""

import json

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
    abort,
)
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Faculty, Department, Programme
from app.models.application import ApplicationStatus, DocumentType
from app.utils.decorators import roles_required
from app.blueprints.applicant.forms import (
    ProfileForm,
    ApplicationForm,
    DocumentUploadForm,
)
from app.services import (
    application_service,
    file_service,
    auth_service,
)


applicant_bp = Blueprint("applicant", __name__)


def _guard():
    """Ensure the logged-in user has a profile; abort 403 for non-applicants."""
    if not current_user.is_applicant:
        abort(403)

    return current_user.applicant_profile


@applicant_bp.route("/dashboard")
@login_required
@roles_required("applicant")
def dashboard():
    profile = _guard()

    application, error = (
        application_service.get_or_create_draft_application(profile)
    )

    if error:
        flash(error, "warning")

    checklist = (
        application_service.get_completeness_checklist(
            profile,
            application,
        )
        if application
        else []
    )

    ready = (
        application_service.is_ready_to_submit(
            profile,
            application,
        )
        if application
        else False
    )

    unread_notifications = (
        current_user.notifications
        .filter_by(is_read=False)
        .count()
    )

    return render_template(
        "applicant/dashboard.html",
        profile=profile,
        application=application,
        checklist=checklist,
        ready=ready,
        unread_notifications=unread_notifications,
    )


@applicant_bp.route("/profile", methods=["GET", "POST"])
@login_required
@roles_required("applicant")
def profile():
    profile = _guard()
    form = ProfileForm(obj=profile)

    if form.validate_on_submit():
        form.populate_obj(profile)

        if form.passport_photo.data:
            file_info = file_service.save_file(
                form.passport_photo.data,
                "PASSPORT_UPLOAD_SUBDIR",
            )

            file_service.delete_file(
                profile.passport_photo_path
            )

            profile.passport_photo_path = file_info["file_path"]

        profile.profile_completed = True

        db.session.commit()

        auth_service.log_action(
            actor_id=current_user.id,
            action="PROFILE_UPDATED",
            entity_type="ApplicantProfile",
            entity_id=profile.id,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
        )

        flash(
            "Profile saved successfully.",
            "success",
        )

        return redirect(
            url_for("applicant.dashboard")
        )

    return render_template(
        "applicant/profile.html",
        form=form,
        profile=profile,
    )


def _populate_programme_choices(form):
    form.faculty_id.choices = [
        (f.id, f.name)
        for f in Faculty.query
        .filter_by(is_active=True)
        .order_by(Faculty.name)
    ]

    form.department_id.choices = [
        (d.id, d.name)
        for d in Department.query
        .filter_by(is_active=True)
        .order_by(Department.name)
    ]

    form.programme_id.choices = [
        (p.id, p.name)
        for p in Programme.query
        .filter_by(is_active=True)
        .order_by(Programme.name)
    ]


@applicant_bp.route("/application", methods=["GET", "POST"])
@login_required
@roles_required("applicant")
def application_form():
    profile = _guard()

    application, error = (
        application_service.get_or_create_draft_application(profile)
    )

    if error:
        flash(error, "error")
        return redirect(
            url_for("applicant.dashboard")
        )

    if application.id and application.status != ApplicationStatus.DRAFT:
        flash(
            "Your application has already been submitted and can no longer be edited.",
            "info",
        )

        return redirect(
            url_for("applicant.application_status")
        )

    form = ApplicationForm()

    _populate_programme_choices(form)

    if request.method == "GET":
        if application.programme_id:
            form.programme_id.data = application.programme_id
            form.department_id.data = (
                application.programme.department_id
            )
            form.faculty_id.data = (
                application.programme.department.faculty_id
            )

        form.utme_registration_number.data = (
            application.utme_registration_number
        )

        form.utme_score.data = application.utme_score

        form.olevel_exam_type.data = (
            application.olevel_exam_type
        )

        form.olevel_exam_year.data = (
            application.olevel_exam_year
        )

        if application.utme_subjects_json:
            saved = json.loads(
                application.utme_subjects_json
            )

            for i, entry in enumerate(saved[:4]):
                form.utme_subjects.entries[i].form.subject.data = (
                    entry.get("subject")
                )

                form.utme_subjects.entries[i].form.score.data = (
                    entry.get("score")
                )

        if application.olevel_results_json:
            saved = json.loads(
                application.olevel_results_json
            )

            for i, entry in enumerate(saved[:9]):
                form.olevel_results.entries[i].form.subject.data = (
                    entry.get("subject")
                )

                form.olevel_results.entries[i].form.grade.data = (
                    entry.get("grade")
                )

    if form.validate_on_submit():
        programme = Programme.query.get(
            form.programme_id.data
        )

        if (
            not programme
            or programme.department_id != form.department_id.data
        ):
            flash(
                "Selected programme does not match the selected department.",
                "error",
            )

            return render_template(
                "applicant/application_form.html",
                form=form,
                application=application,
            )

        if (
            programme.department.faculty_id
            != form.faculty_id.data
        ):
            flash(
                "Selected department does not match the selected faculty.",
                "error",
            )

            return render_template(
                "applicant/application_form.html",
                form=form,
                application=application,
            )

        utme_subjects = [
            {
                "subject": entry.form.subject.data,
                "score": entry.form.score.data,
            }
            for entry in form.utme_subjects.entries
            if entry.form.subject.data
        ]

        olevel_results = [
            {
                "subject": entry.form.subject.data,
                "grade": entry.form.grade.data,
            }
            for entry in form.olevel_results.entries
            if (
                entry.form.subject.data
                and entry.form.grade.data
            )
        ]

        application_service.save_academic_details(
            application,
            programme_id=form.programme_id.data,
            utme_registration_number=(
                form.utme_registration_number.data
            ),
            utme_score=form.utme_score.data,
            utme_subjects=utme_subjects,
            olevel_exam_type=form.olevel_exam_type.data,
            olevel_exam_year=form.olevel_exam_year.data,
            olevel_results=olevel_results,
        )

        flash(
            "Application details saved.",
            "success",
        )

        return redirect(
            url_for("applicant.application_documents")
        )

    return render_template(
        "applicant/application_form.html",
        form=form,
        application=application,
    )


@applicant_bp.route(
    "/application/documents",
    methods=["GET", "POST"],
)
@login_required
@roles_required("applicant")
def application_documents():
    profile = _guard()

    application, error = (
        application_service.get_or_create_draft_application(profile)
    )

    if error or not application or not application.id:
        flash(
            "Please complete your application details before uploading documents.",
            "warning",
        )

        return redirect(
            url_for("applicant.application_form")
        )

    if application.status != ApplicationStatus.DRAFT:
        flash(
            "Your application has already been submitted and can no longer be edited.",
            "info",
        )

        return redirect(
            url_for("applicant.application_status")
        )

    form = DocumentUploadForm()

    field_to_doctype = {
        "olevel_result": DocumentType.OLEVEL_RESULT,
        "utme_result_slip": DocumentType.UTME_RESULT_SLIP,
        "birth_certificate": DocumentType.BIRTH_CERTIFICATE,
        "lga_certificate": DocumentType.LGA_CERTIFICATE,
    }

    if form.validate_on_submit():
        uploaded_any = False

        for field_name, doc_type in field_to_doctype.items():
            field = getattr(form, field_name)

            if field.data:
                file_info = file_service.save_file(
                    field.data,
                    "DOCUMENT_UPLOAD_SUBDIR",
                )

                application_service.replace_document(
                    application,
                    doc_type,
                    file_info,
                )

                uploaded_any = True

        if uploaded_any:
            flash(
                "Documents uploaded successfully.",
                "success",
            )
        else:
            flash(
                "No new files were selected.",
                "info",
            )

        return redirect(
            url_for("applicant.application_preview")
        )

    documents = (
        application_service.get_uploaded_document_map(
            application
        )
    )

    return render_template(
        "applicant/documents.html",
        form=form,
        application=application,
        documents=documents,
    )


@applicant_bp.route("/application/preview")
@login_required
@roles_required("applicant")
def application_preview():
    profile = _guard()

    application, error = (
        application_service.get_or_create_draft_application(profile)
    )

    if error or not application or not application.id:
        flash(
            "Please complete your application details first.",
            "warning",
        )

        return redirect(
            url_for("applicant.application_form")
        )

    checklist = application_service.get_completeness_checklist(
        profile,
        application,
    )

    ready = application_service.is_ready_to_submit(
        profile,
        application,
    )

    documents = (
        application_service.get_uploaded_document_map(
            application
        )
    )

    utme_subjects = (
        json.loads(application.utme_subjects_json)
        if application.utme_subjects_json
        else []
    )

    olevel_results = (
        json.loads(application.olevel_results_json)
        if application.olevel_results_json
        else []
    )

    return render_template(
        "applicant/preview.html",
        profile=profile,
        application=application,
        checklist=checklist,
        ready=ready,
        documents=documents,
        utme_subjects=utme_subjects,
        olevel_results=olevel_results,
    )


@applicant_bp.route(
    "/application/submit",
    methods=["POST"],
)
@login_required
@roles_required("applicant")
def application_submit():
    profile = _guard()

    application, error = (
        application_service.get_or_create_draft_application(profile)
    )

    if error or not application or not application.id:
        flash(
            "Please complete your application before submitting.",
            "error",
        )

        return redirect(
            url_for("applicant.application_form")
        )

    if application.status != ApplicationStatus.DRAFT:
        flash(
            "This application has already been submitted.",
            "info",
        )

        return redirect(
            url_for("applicant.application_status")
        )

    if not application_service.is_ready_to_submit(
        profile,
        application,
    ):
        flash(
            "Please complete all required sections before submitting.",
            "error",
        )

        return redirect(
            url_for("applicant.application_preview")
        )

    submitted_application, submission_error = (
        application_service.submit_application(
            application
        )
    )

    if submission_error:
        flash(
            submission_error,
            "error",
        )

        return redirect(
            url_for("applicant.application_preview")
        )

    auth_service.log_action(
        actor_id=current_user.id,
        action="APPLICATION_SUBMITTED",
        entity_type="Application",
        entity_id=submitted_application.id,
        description=(
            f"Application "
            f"{submitted_application.application_number} "
            f"submitted"
        ),
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
    )

    flash(
        "Your application has been submitted successfully!",
        "success",
    )

    return redirect(
        url_for("applicant.application_status")
    )


@applicant_bp.route("/application/status")
@login_required
@roles_required("applicant")
def application_status():
    profile = _guard()

    application, error = (
        application_service.get_or_create_draft_application(profile)
    )

    if error:
        flash(
            error,
            "warning",
        )

    return render_template(
        "applicant/status.html",
        profile=profile,
        application=application,
    )


@applicant_bp.route("/application/admission-letter")
@login_required
@roles_required("applicant")
def admission_letter():
    profile = _guard()

    application, _ = (
        application_service.get_or_create_draft_application(profile)
    )

    if (
        not application
        or application.status != ApplicationStatus.APPROVED
    ):
        flash(
            "Your admission letter is not available yet.",
            "info",
        )

        return redirect(
            url_for("applicant.application_status")
        )

    letter = (
        application.decision.admission_letter
        if application.decision
        else None
    )

    if not letter:
        flash(
            "Your admission letter is being processed. Please check back shortly.",
            "info",
        )

        return redirect(
            url_for("applicant.application_status")
        )

    return render_template(
        "applicant/admission_letter.html",
        application=application,
        letter=letter,
        profile=profile,
    )


# --- AJAX endpoints for cascading dropdowns ---

@applicant_bp.route(
    "/api/departments/<int:faculty_id>"
)
@login_required
def api_departments(faculty_id):
    departments = (
        Department.query
        .filter_by(
            faculty_id=faculty_id,
            is_active=True,
        )
        .order_by(Department.name)
        .all()
    )

    return jsonify(
        [
            {
                "id": department.id,
                "name": department.name,
            }
            for department in departments
        ]
    )


@applicant_bp.route(
    "/api/programmes/<int:department_id>"
)
@login_required
def api_programmes(department_id):
    programmes = (
        Programme.query
        .filter_by(
            department_id=department_id,
            is_active=True,
        )
        .order_by(Programme.name)
        .all()
    )

    return jsonify(
        [
            {
                "id": programme.id,
                "name": programme.name,
            }
            for programme in programmes
        ]
    )