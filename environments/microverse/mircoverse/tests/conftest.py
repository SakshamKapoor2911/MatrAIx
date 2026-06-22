"""Shared pytest fixtures.

DB-backed tests skip gracefully when Postgres is unreachable (Docker not started),
so the pure world-core suite always runs. Start the DB with `docker compose up -d`
to exercise the persistence/server/integration tests.
"""

from __future__ import annotations

import asyncio

import pytest

from mircoverse.config import settings
from mircoverse.persistence import db


def _db_available() -> bool:
    try:
        return asyncio.run(db.ping(settings.test_database_url)) or asyncio.run(
            db.ping(settings.database_url)
        )
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="Postgres not reachable — run `docker compose up -d` to enable DB tests",
)
