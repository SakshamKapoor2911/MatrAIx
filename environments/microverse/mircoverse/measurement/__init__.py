"""Engine-driven identity measurement (World.md §9).

Snapshotting the reflective layer on a fixed cadence + a forced end-of-experiment
snapshot, plus the optional cosine *tripwire* (§9.3, never the drift metric).
"""

from mircoverse.measurement.snapshots import (
    TRIGGER_ENGINE_MEASUREMENT,
    TRIGGER_FORCED_END,
    compute_drift_tripwire,
    cosine_distance,
    soul_to_text,
    take_forced_end_snapshot,
    take_measurement_snapshot,
)

__all__ = [
    "TRIGGER_ENGINE_MEASUREMENT",
    "TRIGGER_FORCED_END",
    "compute_drift_tripwire",
    "cosine_distance",
    "soul_to_text",
    "take_forced_end_snapshot",
    "take_measurement_snapshot",
]
