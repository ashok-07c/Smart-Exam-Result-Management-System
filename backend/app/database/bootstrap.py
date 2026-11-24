"""Idempotent deployment bootstrap: migrate the schema and seed once.

This is used by hosts that do not offer shell access. It is opt-in through
``AUTO_BOOTSTRAP=true`` so local development and the test suite keep their
existing behaviour.
"""
from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.database.session import SessionLocal, engine
from app.models.user import User

logger = logging.getLogger("app.bootstrap")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config() -> Config:
    config = Config(str(_PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_PROJECT_ROOT / "migrations"))
    config.set_main_option("prepend_sys_path", str(_PROJECT_ROOT))
    return config


def _prepare_schema() -> None:
    """Upgrade to head, tolerating a database already seeded without Alembic."""
    existing = set(inspect(engine).get_table_names())
    config = _alembic_config()

    if "alembic_version" not in existing and "users" in existing:
        # The seed command creates tables directly. If it ran before Alembic,
        # mark the existing schema as current instead of replaying migrations.
        logger.warning("Schema tables exist without alembic_version; stamping head")
        command.stamp(config, "head")
    else:
        logger.info("Applying Alembic migrations")
        command.upgrade(config, "head")


def _seed_if_empty() -> None:
    with SessionLocal() as db:
        user_count = db.query(User).count()
        if user_count > 0:
            print(f"Users already present ({user_count}); skipping institution seed", flush=True)
            return
        # Imported lazily so the models are registered before the first query.
        from app.database.seed import seed_institution_db

        print("Seeding institution data for the first time", flush=True)
        seed_institution_db(db, None)


def bootstrap_database() -> None:
    """Prepare the database for serving requests. Safe to call on every boot."""
    # Plain prints are used here because Alembic's logging config lowers the
    # root logger level to WARN, which would otherwise hide these milestones.
    print("Database bootstrap started", flush=True)
    try:
        _prepare_schema()
        _seed_if_empty()
    except Exception:
        import traceback

        traceback.print_exc()
        print("Database bootstrap FAILED", flush=True)
        raise
    print("Database bootstrap complete", flush=True)
