"""Bounded marginal calibration and deterministic sampling utilities."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping

import numpy as np


def rake_weights(
    columns: Mapping[str, np.ndarray],
    targets: Mapping[str, Mapping[int, float]],
    *,
    max_iterations: int = 100,
    tolerance: float = 1e-7,
    weight_bounds: tuple[float, float] = (0.05, 20.0),
) -> np.ndarray:
    """Fit bounded nonnegative weights to categorical marginal targets.

    Negative category codes are treated as missing and receive no update for
    that margin. Each target mapping is normalized over its supplied codes.
    """
    if not columns:
        raise ValueError("At least one calibration column is required")
    row_counts = {len(values) for values in columns.values()}
    if len(row_counts) != 1:
        raise ValueError("Calibration columns must have equal length")
    row_count = row_counts.pop()
    lower, upper = weight_bounds
    if not 0 < lower <= upper:
        raise ValueError("Weight bounds must satisfy 0 < lower <= upper")

    weights = np.ones(row_count, dtype=np.float64)
    for _ in range(max_iterations):
        largest_error = 0.0
        for name, raw_target in targets.items():
            values = columns[name]
            known = values >= 0
            known_weight = weights[known].sum()
            target_total = sum(raw_target.values())
            if known_weight == 0 or target_total <= 0:
                continue
            for code, target_share in raw_target.items():
                category = values == code
                current = weights[category].sum()
                desired = known_weight * target_share / target_total
                largest_error = max(largest_error, abs(current - desired) / known_weight)
                if current > 0:
                    weights[category] *= desired / current
            np.clip(weights, lower, upper, out=weights)
            weights /= weights.mean()
        if largest_error <= tolerance:
            break
    return weights


def _inclusion_probabilities(weights: np.ndarray, sample_size: int) -> np.ndarray:
    """Approximate exponential-race inclusion probabilities at fixed size."""
    if sample_size == len(weights):
        return np.ones(len(weights), dtype=np.float64)
    low, high = 0.0, 1.0
    while np.sum(-np.expm1(-high * weights)) < sample_size:
        high *= 2.0
    for _ in range(60):
        midpoint = (low + high) / 2.0
        if np.sum(-np.expm1(-midpoint * weights)) < sample_size:
            low = midpoint
        else:
            high = midpoint
    return -np.expm1(-high * weights)


def calibrate_inclusion_weights(
    columns: Mapping[str, np.ndarray],
    targets: Mapping[str, Mapping[int, float]],
    sample_size: int,
    *,
    max_iterations: int = 200,
    tolerance: float = 1e-7,
    weight_bounds: tuple[float, float] = (0.001, 1_000.0),
) -> np.ndarray:
    """Fit race weights whose fixed-size inclusion margins match targets."""
    if not columns:
        raise ValueError("At least one calibration column is required")
    row_counts = {len(values) for values in columns.values()}
    if len(row_counts) != 1:
        raise ValueError("Calibration columns must have equal length")
    row_count = row_counts.pop()
    if not 0 < sample_size <= row_count:
        raise ValueError("sample_size must be positive and no larger than the pool")
    lower, upper = weight_bounds
    weights = np.ones(row_count, dtype=np.float64)
    for _ in range(max_iterations):
        largest_error = 0.0
        for name, raw_target in targets.items():
            probabilities = _inclusion_probabilities(weights, sample_size)
            values = columns[name]
            known = values >= 0
            known_total = probabilities[known].sum()
            target_total = sum(raw_target.values())
            if known_total == 0 or target_total <= 0:
                continue
            for code, target_share in raw_target.items():
                category = values == code
                current = probabilities[category].sum()
                desired = known_total * target_share / target_total
                largest_error = max(largest_error, abs(current - desired) / known_total)
                if current > 0:
                    weights[category] *= desired / current
            np.clip(weights, lower, upper, out=weights)
            weights /= np.exp(np.mean(np.log(weights)))
        if largest_error <= tolerance:
            break
    return weights


def deterministic_priority_sample(
    stable_ids: Iterable[str], weights: np.ndarray, sample_size: int, seed: int
) -> np.ndarray:
    """Return indices for weighted sampling without replacement.

    Exponential-race priorities make the result independent of input order.
    """
    if not 0 <= sample_size <= len(weights):
        raise ValueError("sample_size must be between zero and the pool size")
    if np.any(weights <= 0):
        raise ValueError("All sampling weights must be positive")
    priorities = np.empty(len(weights), dtype=np.float64)
    seen = 0
    for index, stable_id in enumerate(stable_ids):
        if index >= len(weights):
            raise ValueError("stable_ids and weights must have equal length")
        digest = hashlib.blake2b(
            f"{seed}:{stable_id}".encode("utf-8"), digest_size=8
        ).digest()
        uniform = (int.from_bytes(digest, "big") + 0.5) / 2**64
        priorities[index] = -np.log(uniform) / weights[index]
        seen += 1
    if seen != len(weights):
        raise ValueError("stable_ids and weights must have equal length")
    if sample_size == len(weights):
        return np.argsort(priorities)
    selected = np.argpartition(priorities, sample_size)[:sample_size]
    return selected[np.argsort(priorities[selected])]


def marginal_shares(values: np.ndarray, selected: np.ndarray) -> dict[int, float]:
    """Compute known-value category shares for selected row indices."""
    chosen = values[selected]
    chosen = chosen[chosen >= 0]
    if not len(chosen):
        return {}
    codes, counts = np.unique(chosen, return_counts=True)
    return {int(code): float(count / len(chosen)) for code, count in zip(codes, counts)}
