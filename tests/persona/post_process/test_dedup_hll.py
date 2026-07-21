from __future__ import annotations

import numpy as np

from persona.post_process.deduplication.hll import estimate_cardinality, update_registers


def test_hll_estimates_known_cardinality() -> None:
    registers = np.zeros(1 << 16, dtype=np.uint8)
    values = np.arange(1_000_000, dtype=np.uint64)
    update_registers(registers, values, 16)

    estimate = estimate_cardinality(registers)

    assert abs(estimate - len(values)) / len(values) < 0.015


def test_hll_merge_is_registerwise_maximum() -> None:
    left = np.zeros(1 << 12, dtype=np.uint8)
    right = np.zeros(1 << 12, dtype=np.uint8)
    update_registers(left, np.arange(0, 100_000, dtype=np.uint64), 12)
    update_registers(right, np.arange(100_000, 200_000, dtype=np.uint64), 12)

    merged = np.maximum(left, right)
    estimate = estimate_cardinality(merged)

    assert abs(estimate - 200_000) / 200_000 < 0.04