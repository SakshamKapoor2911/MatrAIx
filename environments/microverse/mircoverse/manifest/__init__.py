"""Experiment manifest + world generation (BUILD_SPEC §7, Protocol.md §9).

The manifest is the run's reproducibility contract; the generators turn it into an initial
world-core ``WorldState``. Everything stochastic flows through the single seeded RNG
(``seeded_rng``), so identical seed => identical world (World.md §11).
"""

from mircoverse.manifest.generators import (
    gen_scale_world,
    gen_seed_world,
    generate_world,
    scale_manifest,
    seed_manifest,
)
from mircoverse.manifest.loader import (
    dump_manifest,
    load_manifest,
    save_manifest,
    seeded_rng,
    validate_manifest,
)
from mircoverse.manifest.schema import (
    SCHEMA_VERSION,
    ActionCosts,
    AgentSpec,
    ExperimentManifest,
    GridConfig,
    PressureSchedule,
    ResourceDistribution,
    SiphonCurve,
    TerrainDistribution,
)

__all__ = [
    "SCHEMA_VERSION",
    "ExperimentManifest",
    "GridConfig",
    "TerrainDistribution",
    "ResourceDistribution",
    "SiphonCurve",
    "PressureSchedule",
    "ActionCosts",
    "AgentSpec",
    "load_manifest",
    "validate_manifest",
    "dump_manifest",
    "save_manifest",
    "seeded_rng",
    "generate_world",
    "seed_manifest",
    "scale_manifest",
    "gen_seed_world",
    "gen_scale_world",
]
