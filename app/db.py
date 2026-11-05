"""SQLite connection handling and CLI commands.

SQLite keeps the MVP dependency-free. The schema is plain SQL, so moving to
PostgreSQL later means swapping this module, not rewriting the app.
"""
import sqlite3
from pathlib import Path

import click
from flask import current_app, g


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    schema = (Path(__file__).parent / "schema.sql").read_text()
    db.executescript(schema)
    db.commit()


@click.command("init-db")
def init_db_command():
    """Drop and recreate all tables."""
    init_db()
    click.echo("Database initialised.")


@click.command("seed")
def seed_command():
    """Recreate tables and load demo experts and slots."""
    from .seed import seed

    init_db()
    count = seed(get_db())
    click.echo(f"Seeded {count} experts with open slots.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_command)
