import numpy as np

from persona.post_process.coreset_1m.calibration import (
    calibrate_inclusion_weights,
    deterministic_priority_sample,
    marginal_shares,
)


def test_raking_and_priority_sampling_approach_requested_margins() -> None:
    size = 20_000
    region_block = np.array([0] * 12 + [1] * 5 + [2] * 3)
    columns = {
        "gender": np.repeat(np.array([0, 1]), [16_000, 4_000]),
        "region": np.tile(region_block, size // len(region_block)),
    }
    targets = {"gender": {0: 0.7, 1: 0.3}, "region": {0: 0.4, 1: 0.3, 2: 0.3}}
    weights = calibrate_inclusion_weights(columns, targets, sample_size=5_000)
    selected = deterministic_priority_sample(
        [f"row-{index}" for index in range(size)], weights, 5_000, seed=20260720
    )

    gender = marginal_shares(columns["gender"], selected)
    region = marginal_shares(columns["region"], selected)
    assert abs(gender[0] - 0.7) < 0.03
    assert abs(region[0] - 0.4) < 0.03
    assert abs(region[1] - 0.3) < 0.03


def test_priority_sampling_is_input_order_independent() -> None:
    stable_ids = np.array([f"row-{index}" for index in range(100)])
    weights = np.linspace(0.5, 2.0, 100)
    expected = set(stable_ids[deterministic_priority_sample(stable_ids, weights, 20, 7)])
    order = np.arange(99, -1, -1)
    actual_indices = deterministic_priority_sample(stable_ids[order], weights[order], 20, 7)
    assert set(stable_ids[order][actual_indices]) == expected


def test_priority_sampling_accepts_streaming_ids() -> None:
    weights = np.ones(100)
    selected = deterministic_priority_sample((f"row-{index}" for index in range(100)), weights, 10, 7)
    assert len(selected) == 10