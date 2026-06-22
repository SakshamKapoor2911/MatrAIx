"""Create + migrate N isolated worker databases for the parallel overnight run.

WHY: initialize_simulation WIPES the whole DB at every bootstrap (bootstrap.py step 1). So two runs
cannot share one database — run B's bootstrap would erase run A mid-flight. To run many (arm × seed)
jobs concurrently we give each its OWN database (mircoverse_w0, mircoverse_w1, …); the per-process
pool is keyed by DSN (db.py) and the configs never collide because each child process imports
config.py with a different DATABASE_URL in its environment.

This script connects to the admin `postgres` database, CREATE DATABASE mircoverse_w0..w{N-1}
(idempotent — skips any that already exist), and applies schema.sql to each via dal.migrate(dsn=...).

Usage (Postgres up):
    .venv/Scripts/python.exe scripts/setup_worker_dbs.py --workers 6
    .venv/Scripts/python.exe scripts/setup_worker_dbs.py --workers 6 --drop   # tear down first
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncpg

from mircoverse.config import settings
from mircoverse.persistence import dal

_WORKER_PREFIX = "mircoverse_w"


def worker_dsn(base_dsn: str, n: int) -> str:
    """Return ``base_dsn`` with its database name replaced by ``mircoverse_w{n}``."""
    parts = urlsplit(base_dsn)
    new_path = f"/{_WORKER_PREFIX}{n}"
    return urlunsplit((parts.scheme, parts.netloc, new_path, parts.query, parts.fragment))


def admin_dsn(base_dsn: str) -> str:
    """Same server/credentials as ``base_dsn`` but pointed at the always-present ``postgres`` DB, so
    we can issue CREATE/DROP DATABASE (you cannot drop the DB you are connected to)."""
    parts = urlsplit(base_dsn)
    return urlunsplit((parts.scheme, parts.netloc, "/postgres", parts.query, parts.fragment))


def _db_name(n: int) -> str:
    name = f"{_WORKER_PREFIX}{n}"
    # Defensive: the name is interpolated into a CREATE DATABASE (identifiers can't be parameterized),
    # so assert it matches a strict pattern — never let anything but our own name reach that string.
    assert re.fullmatch(r"mircoverse_w\d+", name), name
    return name


async def setup(n_workers: int, drop: bool) -> None:
    base = settings.database_url
    admin = admin_dsn(base)
    print(f"admin connection: {admin}")
    conn = await asyncpg.connect(admin)
    try:
        for i in range(n_workers):
            name = _db_name(i)
            exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", name)
            if drop and exists:
                # Terminate other backends on that DB, then drop it.
                await conn.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1", name
                )
                await conn.execute(f'DROP DATABASE "{name}"')
                print(f"  dropped {name}")
                exists = None
            if not exists:
                await conn.execute(f'CREATE DATABASE "{name}"')
                print(f"  created {name}")
            else:
                print(f"  {name} already exists — leaving in place")
    finally:
        await conn.close()

    # Migrate each worker DB (idempotent schema.sql).
    for i in range(n_workers):
        dsn = worker_dsn(base, i)
        await dal.migrate(dsn=dsn)
        print(f"  migrated {_db_name(i)}")
    print(f"\n{n_workers} worker DB(s) ready. Pass DATABASE_URL=<worker_dsn> per child process.")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Create + migrate isolated worker databases")
    ap.add_argument("--workers", type=int, required=True, help="number of worker DBs to create")
    ap.add_argument("--drop", action="store_true", help="drop existing worker DBs first (DESTRUCTIVE)")
    args = ap.parse_args()
    asyncio.run(setup(args.workers, args.drop))


if __name__ == "__main__":
    main()
