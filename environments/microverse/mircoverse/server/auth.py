"""Bearer-token auth for the seed-run server (Protocol.md §5.1).

Each agent gets an opaque high-entropy API key at registration. The server NEVER stores
the plaintext key — only its SHA-256 hash lands in ``agents.api_key_hash`` (Architecture.md
API auth). On every request the bearer token is hashed and matched against that column, so a
leaked database cannot reconstruct any agent's key.

These helpers are pure (no I/O): the FastAPI dependency that walks them to a DB row lives in
``app.py`` so this module stays unit-testable without Postgres.
"""

from __future__ import annotations

import hashlib
import secrets

_TOKEN_BYTES = 32  # 256 bits of entropy → a 43-char urlsafe token.


def generate_api_key() -> str:
    """Mint one opaque, high-entropy bearer token. Returned to the agent exactly once."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def hash_api_key(api_key: str) -> str:
    """SHA-256 hex digest of a bearer token — what is persisted in ``agents.api_key_hash``.

    Pure and deterministic, so the same token always maps to the same stored hash and a
    request can be authenticated by hashing its token and matching the column."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def parse_bearer(authorization: str | None) -> str | None:
    """Extract the raw token from an ``Authorization: Bearer <token>`` header.

    Returns the token, or ``None`` if the header is absent or not a well-formed bearer
    header. Case-insensitive on the ``Bearer`` scheme (RFC 6750)."""
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None
