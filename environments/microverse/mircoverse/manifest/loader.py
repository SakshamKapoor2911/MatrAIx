"""Load / validate an experiment manifest from YAML and build its seeded RNG (Protocol.md §9).

Pure functions over the filesystem boundary: ``load_manifest`` reads a YAML file into a validated
``ExperimentManifest``; ``validate_manifest`` validates an already-parsed mapping; ``seeded_rng``
builds the single ``random.Random`` that drives ALL stochastic resolution (World.md §11). The RNG
is derived deterministically from ``manifest.seed`` — never from ``time``, never from a global —
so the same manifest yields the same RNG stream and therefore the same world.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import yaml

from mircoverse.manifest.schema import ExperimentManifest


def load_manifest(path: str | Path) -> ExperimentManifest:
    """Read a YAML manifest file and return a validated ``ExperimentManifest``.

    Raises ``FileNotFoundError`` if the path is missing and ``pydantic.ValidationError`` /
    ``ValueError`` if the contents violate the schema (Protocol.md §9 reproducibility contract).
    """
    text = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if data is None:
        data = {}
    return validate_manifest(data)


def validate_manifest(data: dict[str, Any]) -> ExperimentManifest:
    """Validate a parsed mapping into an ``ExperimentManifest`` (pure, no I/O)."""
    return ExperimentManifest.model_validate(data)


def dump_manifest(manifest: ExperimentManifest) -> str:
    """Serialize a manifest back to YAML text. Round-trips with ``load_manifest`` (Protocol.md §9)."""
    return yaml.safe_dump(manifest.model_dump(mode="json"), sort_keys=False)


def save_manifest(manifest: ExperimentManifest, path: str | Path) -> None:
    """Write a manifest to a YAML file."""
    Path(path).write_text(dump_manifest(manifest), encoding="utf-8")


def seeded_rng(manifest: ExperimentManifest) -> random.Random:
    """Build the single seeded RNG for a run (World.md §11).

    Deterministic in ``manifest.seed`` only: identical seed => identical ``random.Random`` stream
    => identical world generation and tick resolution. Never seeded from the clock or a global.
    """
    return random.Random(manifest.seed)
