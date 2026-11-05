"""CSRF protection and admin login, without extra dependencies."""
import hmac
import secrets
from functools import wraps

from flask import abort, current_app, redirect, request, session, url_for


def csrf_token() -> str:
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


def check_csrf():
    """Reject any state-changing request without a valid token."""
    if request.method != "POST":
        return
    sent = request.form.get("_csrf", "")
    if not sent or not hmac.compare_digest(sent, session.get("_csrf", "")):
        abort(400, description="Your session expired. Reload the page and try again.")


def password_ok(candidate: str) -> bool:
    expected = current_app.config["ADMIN_PASSWORD"]
    return hmac.compare_digest(candidate.encode(), expected.encode())


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def make_ref(prefix: str) -> str:
    """Short, unguessable reference shown to clients, e.g. BK-7F3K9Q2M."""
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return prefix + "-" + "".join(secrets.choice(alphabet) for _ in range(8))
