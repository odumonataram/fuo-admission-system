"""Role-based access control decorator."""

from functools import wraps
from flask import abort
from flask_login import current_user


def roles_required(*role_names):
    """
    Restrict a view to users whose role is in role_names.
    Must be used together with @login_required (or after it).
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not current_user.has_role(*role_names):
                abort(403)
            return view_func(*args, **kwargs)
        return wrapped
    return decorator
