import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from persona.post_process.coreset_1m.build_coreset import (
    calibration_audit,
    decode_calibration_batch,
    discover_synthetic_candidates,
    residual_targets,
)
from persona.post_process.unified_dataset.schema import UNIFIED_SCHEMA


def test_decode_calibration_batch_applies_nulls_and_overrides() -> None:
    packed = bytearray(645)
    packed[0] = 0x21
    nulls = bytearray(162)
    nulls[0] = 0b10
    row = {
        "source": "test",
        "source_row_index": 1,
        "source_record_id": None,
        "attributes": bytes(packed),
        "null_bitmap": bytes(nulls),
        "attribute_overrides": [{"field_index": 0, "value": "legacy"}],
        "has_description": False,
        "descriptions": None,
        "grounding": None,
        "metadata_json": None,
    }
    batch = pa.Table.from_pylist([row], schema=UNIFIED_SCHEMA).to_batches()[0]
    decoded = decode_calibration_batch(batch, [0, 1])
    assert decoded.tolist() == [[-1, -1]]


def test_residual_targets_compensate_human_counts() -> None:
    targets = {"field": {0: 0.5, 1: 0.5}}
    residual, diagnostics = residual_targets(targets, {"field": {0: 80, 1: 20}}, 100)
    assert np.isclose(residual["field"][0], 0.2)
    assert np.isclose(residual["field"][1], 0.8)
    assert diagnostics["field"]["negative_residual_mass"] == 0


def test_calibration_audit_reports_missing_and_error() -> None:
    audit = calibration_audit(
        {"field": {0: 0.5, 1: 0.5}},
        [["a", "b"]],
        ["field"],
        [0],
        {"field": {0: 300_000, 1: 200_000}},
        {"field": {0: 150_000, 1: 250_000}},
    )
    assert audit["field"]["known_rows"] == 900_000
    assert audit["field"]["missing_rows"] == 100_000
    assert audit["field"]["categories"]["a"]["achieved"] == 0.5


def test_synthetic_candidates_are_deterministic_and_spread_across_shards(tmp_path) -> None:
    data_root = tmp_path / "data"
    table = pa.table({"value": [1, 2, 3, 4]})
    for shard in range(100):
        shard_dir = data_root / "synthetic" / f"shard_{shard:04d}"
        shard_dir.mkdir(parents=True)
        for part in range(2):
            pq.write_table(
                table,
                shard_dir / f"part_{part}.parquet",
                row_group_size=2,
            )

    first = discover_synthetic_candidates(data_root, shard_count=40, seed=7)
    second = discover_synthetic_candidates(data_root, shard_count=40, seed=7)

    assert first == second
    assert len(first) == 40
    assert len({path.parent.name for path in first}) == 40
    assert all(row_group in {0, 1} for row_group in first.values())