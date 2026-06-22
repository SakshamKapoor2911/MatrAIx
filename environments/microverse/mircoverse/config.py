"""Runtime configuration. Local-first; the same settings shape maps to AWS later."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    # Local Postgres (docker-compose.yml). Same SQL runs on Aurora later.
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://mircoverse:mircoverse@localhost:5432/mircoverse",
    )
    # Separate DB name for the test suite so tests never touch dev data.
    test_database_url: str = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://mircoverse:mircoverse@localhost:5432/mircoverse_test",
    )
    tick_interval_seconds: float = float(os.getenv("TICK_INTERVAL", "30"))


settings = Settings()
