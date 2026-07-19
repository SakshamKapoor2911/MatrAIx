"""Deterministic synthetic display names for bench persona records."""

from __future__ import annotations

import hashlib
from typing import Any

_REGION_POOLS: dict[str, list[tuple[str, str]]] = {
    "East Asia": [
        ("Mei Lin", "Tan"),
        ("Yuki", "Sato"),
        ("Wei", "Zhang"),
        ("Hana", "Kim"),
        ("Jun", "Park"),
        ("Li Wei", "Chen"),
        ("Aiko", "Nakamura"),
        ("Min", "Ho"),
    ],
    "Southeast Asia": [
        ("Anh", "Nguyen"),
        ("Rizal", "Putra"),
        ("Siti", "Rahman"),
        ("Kai", "Lim"),
        ("Mai", "Tran"),
        ("Arif", "Hassan"),
    ],
    "South Asia": [
        ("Arjun", "Mehta"),
        ("Priya", "Sharma"),
        ("Rohan", "Kapoor"),
        ("Anika", "Das"),
        ("Vikram", "Singh"),
        ("Nisha", "Iyer"),
    ],
    "Western Europe": [
        ("Sofia", "Andersson"),
        ("Luka", "Petrov"),
        ("Emma", "Dubois"),
        ("Marco", "Rossi"),
        ("Clara", "Müller"),
        ("Noah", "Bakker"),
    ],
    "Eastern Europe": [
        ("Mila", "Novak"),
        ("Ivan", "Kowalski"),
        ("Elena", "Popescu"),
        ("Tomas", "Horvat"),
        ("Anya", "Volkova"),
        ("Petra", "Jansen"),
    ],
    "North America": [
        ("Jordan", "Lee"),
        ("Maya", "Patel"),
        ("Ethan", "Brooks"),
        ("Sienna", "Carter"),
        ("Noah", "Williams"),
        ("Ava", "Martinez"),
    ],
    "LATAM": [
        ("Camila", "Rojas"),
        ("Diego", "Fernandez"),
        ("Lucia", "Santos"),
        ("Mateo", "Garcia"),
        ("Valentina", "Lopez"),
        ("Andres", "Mendoza"),
    ],
    "MENA": [
        ("Layla", "Haddad"),
        ("Omar", "Khalil"),
        ("Yasmin", "Farouk"),
        ("Karim", "Nasser"),
        ("Nadia", "Rahman"),
        ("Samir", "Aziz"),
    ],
    "Sub-Saharan Africa": [
        ("Amara", "Okafor"),
        ("Kwame", "Mensah"),
        ("Zola", "Ndlovu"),
        ("Amina", "Diallo"),
        ("Tendai", "Moyo"),
        ("Kofi", "Adeyemi"),
    ],
    "Oceania": [
        ("Harper", "Ngata"),
        ("Liam", "Murphy"),
        ("Isla", "Campbell"),
        ("Jack", "Mitchell"),
        ("Ruby", "Taylor"),
        ("Finn", "Walsh"),
    ],
}

_DEFAULT_POOL: list[tuple[str, str]] = [
    ("Jordan", "Lee"),
    ("Maya", "Patel"),
    ("Alex", "Rivera"),
    ("Sam", "Okafor"),
    ("Riley", "Chen"),
    ("Casey", "Brooks"),
    ("Quinn", "Santos"),
    ("Avery", "Kim"),
]


def _hash_index(seed: str, modulo: int) -> int:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % max(modulo, 1)


def synthetic_display_name(
    persona_id: str,
    dimensions: dict[str, Any] | None = None,
) -> str:
    """Return a stable human-readable name for a bench persona."""
    pid = str(persona_id or "").strip()
    dims = dimensions if isinstance(dimensions, dict) else {}
    region = str(dims.get("region") or "").strip()
    pool = _REGION_POOLS.get(region) or _DEFAULT_POOL
    idx = _hash_index(f"{pid}:{region}", len(pool))
    first, last = pool[idx]
    return f"{first} {last}"
