"""SNDBX Experts: connects small businesses with SNDBX advisors."""
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask, render_template

from . import db
from .constants import CATEGORIES, CLIENT_TZ, HUBS
from .security import check_csrf, csrf_token


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        DATABASE=os.environ.get("DATABASE", str(Path(app.instance_path) / "sndbx.sqlite3")),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", "sndbx-admin"),
        PAYMENT_PROVIDER=os.environ.get("PAYMENT_PROVIDER", "simulated"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    app.before_request(check_csrf)
    app.jinja_env.globals.update(
        csrf_token=csrf_token, CATEGORIES=CATEGORIES, HUBS=HUBS, now=datetime.now
    )
    register_filters(app)

    from .admin import bp as admin_bp
    from .public import bp as public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404,
                               message="That page doesn't exist. It may have moved."), 404

    @app.errorhandler(400)
    def bad_request(e):
        return render_template("error.html", code=400, message=e.description), 400

    return app


def register_filters(app: Flask):
    @app.template_filter("kes")
    def kes(amount):
        return f"KES {int(amount):,}"

    @app.template_filter("category")
    def category(key):
        return CATEGORIES.get(key, key)

    @app.template_filter("hubclass")
    def hubclass(hub):
        return "hub-" + HUBS.get(hub, {}).get("colour", "nairobi")

    @app.template_filter("initials")
    def initials(name):
        return "".join(part[0] for part in name.split()[:2]).upper()

    @app.template_filter("slot")
    def slot(iso, hub):
        """'Tue 10 Nov, 10:00 Berlin time (12:00 in Nairobi)'."""
        utc = datetime.fromisoformat(iso)
        local = utc.astimezone(ZoneInfo(HUBS[hub]["tz"]))
        text = f"{local:%a} {local.day} {local:%b, %H:%M}"
        nbo = utc.astimezone(ZoneInfo(CLIENT_TZ))
        if local.utcoffset() != nbo.utcoffset():
            text += f" {hub} time ({nbo:%H:%M} in Nairobi)"
        return text

    def differs_from_nairobi(hub):
        """True when the hub's clock differs from Nairobi's right now."""
        now = datetime.now(ZoneInfo("UTC"))
        return now.astimezone(ZoneInfo(HUBS[hub]["tz"])).utcoffset() != \
            now.astimezone(ZoneInfo(CLIENT_TZ)).utcoffset()

    app.jinja_env.globals["differs_from_nairobi"] = differs_from_nairobi

    @app.template_filter("slotday")
    def slotday(iso, hub):
        local = datetime.fromisoformat(iso).astimezone(ZoneInfo(HUBS[hub]["tz"]))
        return f"{local:%A} {local.day} {local:%B}"

    @app.template_filter("slottime")
    def slottime(iso, hub):
        local = datetime.fromisoformat(iso).astimezone(ZoneInfo(HUBS[hub]["tz"]))
        return local.strftime("%H:%M")

    @app.template_filter("nbotime")
    def nbotime(iso):
        return datetime.fromisoformat(iso).astimezone(ZoneInfo(CLIENT_TZ)).strftime("%H:%M")

    @app.template_filter("datetime")
    def fmt_datetime(iso):
        local = datetime.fromisoformat(iso).astimezone(ZoneInfo(CLIENT_TZ))
        return f"{local.day} {local:%b %Y, %H:%M}"
