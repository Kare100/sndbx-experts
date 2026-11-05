"""Client-facing pages: directory, profiles, request matching, booking."""
import re
from collections import OrderedDict
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import (Blueprint, abort, current_app, flash, redirect, render_template,
                   request, url_for)

from .constants import CATEGORIES, HUBS
from .db import get_db
from .matching import guess_category, match_experts
from .payments import get_provider, normalize_phone
from .security import make_ref

bp = Blueprint("public", __name__)

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def utcnow_iso() -> str:
    return datetime.now(ZoneInfo("UTC")).isoformat()


def open_slots(expert_id: int):
    return get_db().execute(
        """SELECT * FROM availability
           WHERE expert_id = ? AND is_booked = 0 AND start_at > ?
           ORDER BY start_at""",
        (expert_id, utcnow_iso()),
    ).fetchall()


def get_expert_or_404(slug: str):
    expert = get_db().execute(
        "SELECT * FROM experts WHERE slug = ? AND is_active = 1", (slug,)
    ).fetchone()
    if expert is None:
        abort(404)
    return expert


def validate_contact(form) -> tuple[dict, dict]:
    """Return (clean values, errors) for name/email/phone fields."""
    data = {
        "name": form.get("name", "").strip(),
        "email": form.get("email", "").strip().lower(),
        "phone": normalize_phone(form.get("phone", "")),
    }
    errors = {}
    if len(data["name"]) < 2:
        errors["name"] = "Enter your full name."
    if not EMAIL.match(data["email"]):
        errors["email"] = "Enter an email address like name@business.co.ke."
    if not data["phone"]:
        errors["phone"] = "Enter a phone number like 0712 345 678, or +1… for other countries."
    return data, errors


@bp.route("/")
def home():
    db = get_db()
    featured = db.execute(
        "SELECT * FROM experts WHERE is_active = 1 ORDER BY rating DESC, sessions_done DESC LIMIT 4"
    ).fetchall()
    hub_counts = {
        row["hub"]: row["n"]
        for row in db.execute("SELECT hub, COUNT(*) AS n FROM experts WHERE is_active = 1 GROUP BY hub")
    }
    return render_template("home.html", featured=featured, hub_counts=hub_counts)


@bp.route("/experts")
def experts():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "")
    hub = request.args.get("hub", "")

    sql = "SELECT * FROM experts WHERE is_active = 1"
    params: list = []
    if category in CATEGORIES:
        sql += " AND category = ?"
        params.append(category)
    if hub in HUBS:
        sql += " AND hub = ?"
        params.append(hub)
    if q:
        sql += " AND (name LIKE ? OR title LIKE ? OR skills LIKE ? OR bio LIKE ?)"
        params += [f"%{q}%"] * 4
    sql += " ORDER BY rating DESC, sessions_done DESC"

    results = get_db().execute(sql, params).fetchall()
    return render_template("experts.html", experts=results, q=q, category=category, hub=hub)


@bp.route("/experts/<slug>")
def expert(slug):
    expert = get_expert_or_404(slug)
    days: OrderedDict = OrderedDict()
    tz = ZoneInfo(HUBS[expert["hub"]]["tz"])
    for s in open_slots(expert["id"]):
        key = datetime.fromisoformat(s["start_at"]).astimezone(tz).date()
        days.setdefault(key, []).append(s)
    request_ref = request.args.get("request", "")
    return render_template("expert.html", expert=expert, days=days,
                           request_ref=request_ref, form={}, errors={})


@bp.route("/experts/<slug>/book", methods=["POST"])
def book(slug):
    db = get_db()
    expert = get_expert_or_404(slug)
    data, errors = validate_contact(request.form)
    notes = request.form.get("notes", "").strip()[:2000]
    request_ref = request.form.get("request_ref", "")

    slot_id = request.form.get("slot_id", type=int)
    slot = None
    if slot_id:
        slot = db.execute(
            "SELECT * FROM availability WHERE id = ? AND expert_id = ? AND start_at > ?",
            (slot_id, expert["id"], utcnow_iso()),
        ).fetchone()
    if slot is None:
        errors["slot_id"] = "Choose a time for your session."

    def show_form_again(status=400):
        days: OrderedDict = OrderedDict()
        tz = ZoneInfo(HUBS[expert["hub"]]["tz"])
        for s in open_slots(expert["id"]):
            days.setdefault(datetime.fromisoformat(s["start_at"]).astimezone(tz).date(), []).append(s)
        return render_template("expert.html", expert=expert, days=days, request_ref=request_ref,
                               form=request.form, errors=errors), status

    if errors:
        return show_form_again()

    # Claim the slot atomically so two clients can't book the same time.
    claimed = db.execute(
        "UPDATE availability SET is_booked = 1 WHERE id = ? AND is_booked = 0", (slot["id"],)
    ).rowcount
    if not claimed:
        db.rollback()
        errors["slot_id"] = "Someone just booked that time. Choose another one."
        return show_form_again(409)

    linked_request = None
    if request_ref:
        linked_request = db.execute(
            "SELECT id FROM client_requests WHERE ref = ?", (request_ref,)
        ).fetchone()

    ref = make_ref("BK")
    payment = get_provider(current_app.config).request_payment(
        data["phone"], expert["rate"], ref
    )
    db.execute(
        """INSERT INTO bookings (ref, expert_id, slot_id, request_id, client_name, email, phone,
               notes, amount, currency, payment_status, payment_ref, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (ref, expert["id"], slot["id"], linked_request["id"] if linked_request else None,
         data["name"], data["email"], data["phone"], notes, expert["rate"], expert["currency"],
         "requested" if payment.ok else "unpaid", payment.reference, utcnow_iso()),
    )
    if linked_request:
        db.execute("UPDATE client_requests SET status = 'matched' WHERE id = ?", (linked_request["id"],))
    db.commit()
    flash(payment.message)
    return redirect(url_for("public.booking", ref=ref))


@bp.route("/bookings/<ref>")
def booking(ref):
    row = get_db().execute(
        """SELECT b.*, e.name AS expert_name, e.title AS expert_title, e.hub, e.slug,
                  a.start_at
           FROM bookings b
           JOIN experts e ON e.id = b.expert_id
           JOIN availability a ON a.id = b.slot_id
           WHERE b.ref = ?""",
        (ref,),
    ).fetchone()
    if row is None:
        abort(404)
    return render_template("booking.html", b=row)


@bp.route("/request", methods=["GET", "POST"])
def new_request():
    if request.method == "GET":
        description = request.args.get("description", "").strip()
        form = {"description": description, "category": guess_category(description) or ""}
        return render_template("request.html", form=form, errors={})

    data, errors = validate_contact(request.form)
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "")
    hub_pref = request.form.get("hub_pref", "")
    company = request.form.get("company", "").strip()[:200]

    if len(description) < 20:
        errors["description"] = "Describe the problem in at least a sentence so we can match you well."
    if category not in CATEGORIES:
        category = guess_category(description) or ""
        if not category:
            errors["category"] = "Choose the area that fits best."
    if hub_pref not in HUBS:
        hub_pref = ""

    if errors:
        return render_template("request.html", form=request.form, errors=errors), 400

    ref = make_ref("RQ")
    db = get_db()
    db.execute(
        """INSERT INTO client_requests (ref, name, email, phone, company, category,
               description, hub_pref, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (ref, data["name"], data["email"], data["phone"], company, category,
         description[:4000], hub_pref or None, utcnow_iso()),
    )
    db.commit()
    return redirect(url_for("public.matches", ref=ref))


@bp.route("/request/<ref>")
def matches(ref):
    db = get_db()
    req = db.execute("SELECT * FROM client_requests WHERE ref = ?", (ref,)).fetchone()
    if req is None:
        abort(404)
    results = match_experts(db, req["category"], req["description"], req["hub_pref"])
    next_slot = {}
    for m in results:
        slots = open_slots(m.expert["id"])
        next_slot[m.expert["id"]] = slots[0]["start_at"] if slots else None
    return render_template("matches.html", req=req, matches=results, next_slot=next_slot)
