"""Async Postgres connection pool. Local now (docker-compose), Aurora-portable later.

The engine talks to Postgres through asyncpg. On the AWS platform the same SQL runs
behind RDS Proxy against Aurora Serverless v2 — nothing in the query layer changes.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg

from mircoverse.config import settings

# A pool is bound to the event loop it was created on, so we cache one pool PER
# (loop, dsn). The seed-run server runs a single long-lived loop (one pool, as before),
# while the test suite spins a fresh `asyncio.run()` loop per test — each gets its own pool
# instead of reusing one bound to an already-closed loop ("Event loop is closed" /
# "another operation is in progress").
_pools: dict[tuple[int, str], asyncpg.Pool] = {}


async def get_pool(dsn: Optional[str] = None) -> asyncpg.Pool:
    resolved = dsn or settings.database_url
    loop = asyncio.get_event_loop()
    key = (id(loop), resolved)
    pool = _pools.get(key)
    if pool is None:
        pool = await asyncpg.create_pool(resolved, min_size=1, max_size=10)
        _pools[key] = pool
    return pool


async def close_pool() -> None:
    """Close the pool for the CURRENT event loop (all dsns), if any."""
    loop = asyncio.get_event_loop()
    for key in [k for k in _pools if k[0] == id(loop)]:
        pool = _pools.pop(key)
        await pool.close()


@asynccontextmanager
async def connection(dsn: Optional[str] = None):
    pool = await get_pool(dsn)
    async with pool.acquire() as conn:
        yield conn


async def ping(dsn: Optional[str] = None) -> bool:
    """True if Postgres is reachable. Used by tests to skip when Docker is down."""
    try:
        conn = await asyncpg.connect(dsn or settings.database_url, timeout=2)
        await conn.execute("SELECT 1")
        await conn.close()
        return True
    except Exception:
        return False
