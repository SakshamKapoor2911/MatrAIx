"""Tests for the pure bearer-token auth helpers (mircoverse.server.auth).

All pure (no DB): key generation entropy, the SHA-256 hash being deterministic + non-plaintext,
and header parsing of the ``Authorization: Bearer <token>`` scheme.
"""

from __future__ import annotations

from mircoverse.server import auth


def test_generate_api_key_is_unique_and_high_entropy():
    """Each minted key is distinct and long enough to be a 256-bit token."""
    keys = {auth.generate_api_key() for _ in range(100)}
    assert len(keys) == 100  # no collisions
    assert all(len(k) >= 40 for k in keys)


def test_hash_api_key_is_deterministic_and_not_plaintext():
    """The hash is stable for a token and never equals (or contains) the plaintext."""
    key = "a-secret-token"
    h1 = auth.hash_api_key(key)
    h2 = auth.hash_api_key(key)
    assert h1 == h2
    assert h1 != key
    assert key not in h1
    assert len(h1) == 64  # sha-256 hex digest


def test_parse_bearer_extracts_token_and_rejects_malformed():
    """parse_bearer returns the token for a well-formed header (case-insensitive scheme) and
    None for missing/garbage headers."""
    assert auth.parse_bearer("Bearer abc123") == "abc123"
    assert auth.parse_bearer("bearer abc123") == "abc123"  # scheme is case-insensitive
    assert auth.parse_bearer(None) is None
    assert auth.parse_bearer("") is None
    assert auth.parse_bearer("Basic abc123") is None
    assert auth.parse_bearer("Bearer") is None  # no token
    assert auth.parse_bearer("Bearer    ") is None  # whitespace-only token
