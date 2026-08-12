"""
QR code service: generates QR code images encoding a verification URL.

The QR code itself never contains personal data — only a URL of the form
https://<domain>/verify/<token>. All personal info is looked up server-side
from the token at verify time (see app/blueprints/verification/routes.py).
"""

import os
import qrcode
from flask import current_app


def generate_qr_code(data: str, filename: str) -> str:
    """
    Generate a QR code image encoding `data` and save it under
    UPLOAD_FOLDER/<QRCODE_SUBDIR>/<filename>.

    Returns the path relative to UPLOAD_FOLDER — safe to store in the DB.
    """
    subdir = current_app.config["QRCODE_SUBDIR"]
    absolute_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], subdir)
    os.makedirs(absolute_dir, exist_ok=True)

    absolute_path = os.path.join(absolute_dir, filename)

    img = qrcode.make(data)
    img.save(absolute_path)

    # IMPORTANT: this path is stored in the DB and used to build URLs
    # (via url_for('static', ...)), so it must always use forward slashes —
    # os.path.join would produce backslashes on Windows, breaking the URL.
    return f"{subdir}/{filename}"
