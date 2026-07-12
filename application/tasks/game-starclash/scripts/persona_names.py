"""Deterministic random display names for arena personas.

Names are derived from the game seed + persona id so the same crew always
gets the same call-signs across runs, without exposing internal persona ids
like "Persona 0001" in the UI.
"""

from __future__ import annotations

import random

_CALLSIGNS = (
    "Nova", "Kai", "Zara", "Orin", "Lyra", "Dex", "Mira", "Jax", "Rhea", "Vex",
    "Sable", "Cyrus", "Nyx", "Arlo", "Vera", "Kade", "Iris", "Rook", "Tess", "Quinn",
    "Blaze", "Wren", "Holt", "Cleo", "Finn", "Skye", "Dax", "Luna", "Gage", "Nell",
)

_SURNAMES = (
    "Ashford", "Sterling", "Vance", "Reed", "Cross", "Drake", "Hale", "Mercer",
    "Sloane", "Kepler", "Voss", "Raine", "Torres", "Pike", "Cassidy", "Rowan",
    "Sinclair", "Marlowe", "Kestrel", "Hawke", "Delaney", "Stroud", "Vale", "Cortez",
)


def random_display_name(persona_id: str, seed: int = 42) -> str:
    """Return a stable random human name for ``persona_id`` under ``seed``."""
    rng = random.Random(f"{seed}:{persona_id}")
    return f"{rng.choice(_CALLSIGNS)} {rng.choice(_SURNAMES)}"