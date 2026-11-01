"""
app/auth/decorators.py
------------------------
role_required — the "one decorator line" RBAC pattern described in the
study guide (Slide 2, Step 3; Slide 4 tech stack table).

IMPORTANT (matches the study guide's key point on Slide 3/5): this
decorator only guards *which page loads*. The real security boundary is
inside each route's SQL query (see app/dashboard/routes.py), which is
filtered by role so unauthorised rows are never even fetched from
PostgreSQL — not just hidden in the template.
"""

from functools import wraps
from flask import abort
from flask_login import current_user


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not current_user.has_role(*allowed_roles):
                abort(403)
            return view_func(*args, **kwargs)
        return wrapped
    return decorator
