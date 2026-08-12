"""
File service: handles secure saving of uploaded files (passport photos,
application documents) with randomized filenames to prevent path
traversal and filename collisions.
"""

import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def is_allowed_image(filename: str) -> bool:
    return _extension(filename) in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def is_allowed_document(filename: str) -> bool:
    return _extension(filename) in current_app.config["ALLOWED_DOCUMENT_EXTENSIONS"]


def save_file(file_storage, subdir_key: str) -> dict:
    """
    Save an uploaded FileStorage object under UPLOAD_FOLDER/<subdir>.

    subdir_key must be one of the *_SUBDIR config keys, e.g.
    "PASSPORT_UPLOAD_SUBDIR" or "DOCUMENT_UPLOAD_SUBDIR".

    Returns a dict with original_filename, stored_filename, file_path
    (relative to UPLOAD_FOLDER — safe to store in the DB), file_size_bytes,
    mime_type.
    """
    original_filename = secure_filename(file_storage.filename)
    ext = _extension(original_filename)
    stored_filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex

    subdir = current_app.config[subdir_key]
    absolute_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], subdir)
    os.makedirs(absolute_dir, exist_ok=True)

    absolute_path = os.path.join(absolute_dir, stored_filename)
    file_storage.save(absolute_path)

    return {
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        # IMPORTANT: forward slash on purpose — this path is stored in the DB
        # and used to build URLs (via url_for('static', ...)). os.path.join
        # would produce backslashes on Windows, breaking those URLs.
        "file_path": f"{subdir}/{stored_filename}",
        "file_size_bytes": os.path.getsize(absolute_path),
        "mime_type": file_storage.mimetype,
    }


def delete_file(relative_path: str) -> None:
    """Best-effort delete of a previously saved file (e.g. when replacing a passport photo)."""
    if not relative_path:
        return
    absolute_path = os.path.join(current_app.config["UPLOAD_FOLDER"], relative_path)
    try:
        if os.path.exists(absolute_path):
            os.remove(absolute_path)
    except OSError:
        pass
