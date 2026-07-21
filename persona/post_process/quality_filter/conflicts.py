"""Compile Full DAG hard masks into vectorized synthetic-row checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np


@dataclass(frozen=True)
class CompiledRule:
    rule_id: str
    condition_columns: tuple[int, ...]
    condition_codes: tuple[np.ndarray, ...]
    target_column: int
    bad_codes: np.ndarray


def compile_hard_rules(
    graph: dict[str, Any],
    columns: Iterable[dict[str, Any]],
) -> list[CompiledRule]:
    """Compile hard-zero conditional masks against a codes schema."""
    column_list = list(columns)
    column_by_id = {str(column["id"]): index for index, column in enumerate(column_list)}
    code_by_value = {
        str(column["id"]): {
            str(value): code for code, value in enumerate(column.get("values", []))
        }
        for column in column_list
    }
    rules: list[CompiledRule] = []

    for mask in graph.get("conditional_masks", []):
        if mask.get("bad_value_multiplier") != 0 or not mask.get("bad_values"):
            continue
        target = str(mask["target"])
        if target not in column_by_id:
            continue

        condition_columns: list[int] = []
        condition_codes: list[np.ndarray] = []
        missing_condition = False
        for field_id, values in mask.get("condition", {}).items():
            field_id = str(field_id)
            if field_id not in column_by_id:
                missing_condition = True
                break
            condition_columns.append(column_by_id[field_id])
            condition_codes.append(
                np.asarray([code_by_value[field_id][str(value)] for value in values], dtype=np.uint8)
            )
        if missing_condition:
            continue

        rules.append(
            CompiledRule(
                rule_id=str(mask["mask_id"]),
                condition_columns=tuple(condition_columns),
                condition_codes=tuple(condition_codes),
                target_column=column_by_id[target],
                bad_codes=np.asarray(
                    [code_by_value[target][str(value)] for value in mask["bad_values"]],
                    dtype=np.uint8,
                ),
            )
        )
    return rules


def evaluate_hard_conflicts(
    codes: np.ndarray,
    rules: Iterable[CompiledRule],
) -> tuple[np.ndarray, dict[str, int]]:
    """Return a row rejection mask and nonzero violation counts by rule."""
    rejected = np.zeros(codes.shape[0], dtype=np.bool_)
    counts: dict[str, int] = {}
    for rule in rules:
        matched = np.ones(codes.shape[0], dtype=np.bool_)
        for column, allowed_codes in zip(rule.condition_columns, rule.condition_codes):
            matched &= np.isin(codes[:, column], allowed_codes)
        matched &= np.isin(codes[:, rule.target_column], rule.bad_codes)
        count = int(np.count_nonzero(matched))
        if count:
            counts[rule.rule_id] = count
            rejected |= matched
    return rejected, counts