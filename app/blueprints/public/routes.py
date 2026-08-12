"""
Public blueprint: the unauthenticated marketing / information site
(landing page, admission news, requirements, FAQ, contact, verification entry).
"""

from flask import Blueprint, render_template

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def home():
    return render_template("public/home.html")


@public_bp.route("/programmes")
def programmes():
    from app.models import Faculty
    faculties = Faculty.query.filter_by(is_active=True).all()
    return render_template("public/programmes.html", faculties=faculties)


@public_bp.route("/requirements")
def requirements():
    return render_template("public/requirements.html")


@public_bp.route("/application-guide")
def application_guide():
    return render_template("public/application_guide.html")


@public_bp.route("/faq")
def faq():
    return render_template("public/faq.html")


@public_bp.route("/contact")
def contact():
    return render_template("public/contact.html")
