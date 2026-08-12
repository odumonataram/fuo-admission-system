"""
Application configuration.

Loads settings from environment variables (via .env in development).
Never hard-code secrets here — this file is safe to commit; the .env file is not.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


class BaseConfig:
    """Shared configuration across all environments."""

    # --- Core Flask ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-do-not-use-in-production")
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://192.168.1.34:5000")

    # --- Database ---
    # DB_ENGINE options:
    #   "sqlite"        -> local file-based DB, zero setup, great for development
    #   "mysql+pymysql" -> production MySQL (default)
    DB_ENGINE = os.environ.get("DB_ENGINE", "mysql+pymysql")
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "3306")
    DB_NAME = os.environ.get("DB_NAME", "fuo_admission_system")

    if DB_ENGINE == "sqlite":
        # Stored under instance/ so it's git-ignored and per-machine.
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'app.db')}"
        SQLALCHEMY_ENGINE_OPTIONS = {}
    else:
        SQLALCHEMY_DATABASE_URI = (
            f"{DB_ENGINE}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
            "?charset=utf8mb4"
        )
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            "pool_recycle": 280,
        }

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- File uploads ---
    UPLOAD_FOLDER = os.path.join(BASE_DIR, os.environ.get("UPLOAD_FOLDER", "app/static/uploads"))
    PASSPORT_UPLOAD_SUBDIR = "passports"
    DOCUMENT_UPLOAD_SUBDIR = "documents"
    QRCODE_SUBDIR = "qrcodes"
    ADMISSION_LETTER_SUBDIR = "admission_letters"
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH_MB", 5)) * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}
    ALLOWED_DOCUMENT_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

    # --- Session / security ---
    PERMANENT_SESSION_LIFETIME = timedelta(
        minutes=int(os.environ.get("SESSION_TIMEOUT_MINUTES", 30))
    )
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = int(os.environ.get("WTF_CSRF_TIME_LIMIT", 3600))
    BCRYPT_LOG_ROUNDS = int(os.environ.get("BCRYPT_LOG_ROUNDS", 12))

    # --- Mail ---
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = _bool(os.environ.get("MAIL_USE_TLS"), True)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "admissions@fuotuoke.edu.ng")

    # --- Application-specific ---
    CURRENT_ACADEMIC_SESSION = os.environ.get("CURRENT_ACADEMIC_SESSION", "2025/2026")
    ITEMS_PER_PAGE = 20

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_ECHO = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

    @staticmethod
    def init_app(app):
        BaseConfig.init_app(app)
        # In production, fail loudly if a real secret key was not set.
        if app.config["SECRET_KEY"] == "dev-key-do-not-use-in-production":
            raise RuntimeError(
                "SECRET_KEY environment variable must be set in production."
            )


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
