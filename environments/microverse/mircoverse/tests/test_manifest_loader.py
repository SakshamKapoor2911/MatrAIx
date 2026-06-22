"""Unit tests for manifest load/validate/dump + seeded RNG (mircoverse.manifest.loader)."""

from __future__ import annotations

from pathlib import Path

from mircoverse.contracts import SoulFile
from mircoverse.manifest.loader import (
    dump_manifest,
    load_manifest,
    save_manifest,
    seeded_rng,
    validate_manifest,
)
from mircoverse.manifest.schema import AgentSpec, ExperimentManifest, GridConfig, SiphonCurve


def _manifest_with_roster() -> ExperimentManifest:
    roster = [
        AgentSpec(agent_id="agent_0", name="Kael", original_soul=SoulFile(core_values=["Keep my word"])),
        AgentSpec(agent_id="agent_1", name="Mira", original_soul=SoulFile(moral_boundaries=["No killing"])),
    ]
    return ExperimentManifest(
        seed=7,
        population=2,
        grid=GridConfig(width=20, height=20),
        siphon=SiphonCurve(pos=(10, 10), base_units=37),
        roster=roster,
    )


def test_validate_manifest_from_mapping() -> None:
    m = validate_manifest({"seed": 3, "population": 25})
    assert m.seed == 3 and m.population == 25


def test_dump_manifest_is_yaml_text() -> None:
    text = dump_manifest(ExperimentManifest(seed=99))
    assert "seed: 99" in text
    assert "schema_version" in text


def test_load_manifest_round_trips(tmp_path: Path) -> None:
    original = _manifest_with_roster()
    path = tmp_path / "run.yaml"
    save_manifest(original, path)
    loaded = load_manifest(path)
    assert loaded == original
    assert loaded.roster[0].original_soul.core_values == ["Keep my word"]


def test_save_manifest_writes_file(tmp_path: Path) -> None:
    path = tmp_path / "out.yaml"
    save_manifest(ExperimentManifest(seed=5), path)
    assert path.exists() and "seed: 5" in path.read_text(encoding="utf-8")


def test_seeded_rng_is_deterministic_in_seed() -> None:
    m = ExperimentManifest(seed=42)
    r1, r2 = seeded_rng(m), seeded_rng(m)
    seq1 = [r1.random() for _ in range(5)]
    seq2 = [r2.random() for _ in range(5)]
    assert seq1 == seq2
    # A different seed yields a different stream.
    other = [x for x in (seeded_rng(ExperimentManifest(seed=43)).random() for _ in range(5))]
    assert other != seq1
