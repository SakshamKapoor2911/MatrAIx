"""Small vectorized HyperLogLog implementation for uint64 signatures."""

from __future__ import annotations

import math

import numpy as np


_MASK64 = np.uint64(0xFFFFFFFFFFFFFFFF)


def splitmix64(values: np.ndarray) -> np.ndarray:
    """Hash uint64 values with the SplitMix64 finalizer."""
    hashed = values.astype(np.uint64, copy=True)
    hashed = (hashed + np.uint64(0x9E3779B97F4A7C15)) & _MASK64
    hashed = ((hashed ^ (hashed >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)) & _MASK64
    hashed = ((hashed ^ (hashed >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)) & _MASK64
    return hashed ^ (hashed >> np.uint64(31))


def update_registers(registers: np.ndarray, signatures: np.ndarray, precision: int) -> None:
    """Update HLL registers from categorical projection signatures."""
    hashed = splitmix64(signatures)
    indices = (hashed & np.uint64((1 << precision) - 1)).astype(np.intp)
    remaining = hashed >> np.uint64(precision)
    width = 64 - precision
    ranks = np.full(remaining.shape, width + 1, dtype=np.uint8)
    nonzero = remaining != 0
    if np.any(nonzero):
        highest_bit = np.floor(np.log2(remaining[nonzero])).astype(np.int16)
        ranks[nonzero] = (width - highest_bit).astype(np.uint8)
    np.maximum.at(registers, indices, ranks)


def estimate_cardinality(registers: np.ndarray) -> float:
    """Estimate cardinality with standard HLL and small-range correction."""
    register_count = len(registers)
    if register_count < 16 or register_count & (register_count - 1):
        raise ValueError("HLL register count must be a power of two >= 16")
    if register_count == 16:
        alpha = 0.673
    elif register_count == 32:
        alpha = 0.697
    elif register_count == 64:
        alpha = 0.709
    else:
        alpha = 0.7213 / (1.0 + 1.079 / register_count)
    estimate = alpha * register_count * register_count / float(
        np.exp2(-registers.astype(np.float64)).sum()
    )
    zeros = int(np.count_nonzero(registers == 0))
    if zeros and estimate <= 2.5 * register_count:
        return register_count * math.log(register_count / zeros)
    return estimate