"""SNDBX team dashboard: review requests and manage bookings."""
from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   session, url_for)

from .constants import BOOKING_STATUSES, REQUEST_STATUSES
from .db import get_db
from .security import admin_required, password_ok

bp = Blueprint("admin", __name__, url_prefix="/admin")


def safe_next(target: str | None) -> str:
    # Only allow redirects back into the admin area, never to another site.
    if target and target.startswith("/admin") and not target.startswith("//"):
        return target
    return url_for("admin.dashboard")


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if password_ok(request.form.get("password", "")):
            session.clear()
            session["is_admin"] = True
            return redirect(safe_next(request.form.get("next")))
        error = "That password is incorrect."
    return render_template("admin/login.html", error=error, next=request.args.get("next", ""))


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("public.home"))


@bp.route("/")
@admin_required
def dashboard():
    db = get_db()
    status = request.args.get("status", "")
    sql = """SELECT b.*, e.name AS expert_name, e.hub, a.start_at, r.ref AS request_ref
             FROM bookings b
             JOIN experts e ON e.id = b.expert_id
             JOIN availability a ON a.id = b.slot_id
             LEFT JOIN client_requests r ON r.id = b.request_id"""
    params = []
    if status in BOOKING_STATUSES:
        sql += " WHERE b.status = ?"
        params.append(status)
    sql += " ORDER BY a.start_at"
    bookings = db.execute(sql, params).fetchall()

    requests_ = db.execute(
        "SELECT * FROM client_requests ORDER BY created_at DESC LIMIT 50"
    ).fetchall()

    stats = db.execute(
        """SELECT
             (SELECT COUNT(*) FROM client_requests WHERE status = 'new')      AS new_requests,
             (SELECT COUNT(*) FROM bookings WHERE status = 'pending')         AS pending,
             (SELECT COUNT(*) FROM bookings WHERE status IN ('pending','confirmed')) AS upcoming,
             (SELECT COALESCE(SUM(amount), 0) FROM bookings WHERE payment_status = 'paid') AS paid_total
        """
    ).fetchone()
    return render_template("admin/dashboard.html", bookings=bookings, requests=requests_,
                           stats=stats, status=status, BOOKING_STATUSES=BOOKING_STATUSES,
                           REQUEST_STATUSES=REQUEST_STATUSES)


@bp.route("/bookings/<int:booking_id>", methods=["POST"])
@admin_required
def update_booking(booking_id):
    db = get_db()
    b = db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if b is None:
        abort(404)

    action = request.form.get("action")
    if action == "mark_paid":
        db.execute("UPDATE bookings SET payment_status = 'paid' WHERE id = ?", (booking_id,))
        flash(f"Marked {b['ref']} as paid.")
    elif action in BOOKING_STATUSES:
        if action == "cancelled":
            # A cancelled session frees the expert's time again.
            db.execute("UPDATE availability SET is_booked = 0 WHERE id = ?", (b["slot_id"],))
        elif b["status"] == "cancelled":
            # Reopening a cancelled booking only works if nobody took the slot.
            reclaimed = db.execute(
                "UPDATE availability SET is_booked = 1 WHERE id = ? AND is_booked = 0",
                (b["slot_id"],),
            ).rowcount
            if not reclaimed:
                db.rollback()
                flash(f"{b['ref']} can't be reopened: that time has been booked by another client.")
                return redirect(url_for("admin.dashboard"))
        db.execute("UPDATE bookings SET status = ? WHERE id = ?", (action, booking_id))
        flash(f"Booking {b['ref']} is now {action}.")
    else:
        abort(400, description="Unknown action.")
    db.commit()
    return redirect(url_for("admin.dashboard", status=request.form.get("filter", "")))


@bp.route("/requests/<int:request_id>", methods=["POST"])
@admin_required
def update_request(request_id):
    db = get_db()
    status = request.form.get("status")
    if status not in REQUEST_STATUSES:
        abort(400, description="Unknown status.")
    updated = db.execute(
        "UPDATE client_requests SET status = ? WHERE id = ?", (status, request_id)
    ).rowcount
    if not updated:
        abort(404)
    db.commit()
    flash(f"Request marked {status}.")
    return redirect(url_for("admin.dashboard") + "#requests")
