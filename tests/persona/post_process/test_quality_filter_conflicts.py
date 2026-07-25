from __future__ import annotations

import numpy as np

from persona.post_process.quality_filter.conflicts import (
    compile_hard_rules,
    evaluate_hard_conflicts,
)


def test_compiles_and_evaluates_hard_conflicts() -> None:
    columns = [
        {"id": "age", "values": ["minor", "adult"]},
        {"id": "employment", "values": ["student", "worker"]},
        {"id": "experience", "values": ["none", "long", "very long"]},
    ]
    graph = {
        "conditional_masks": [
            {
                "mask_id": "minor_long_experience",
                "target": "experience",
                "condition": {"age": ["minor"]},
                "bad_values": ["long", "very long"],
                "bad_value_multiplier": 0,
            },
            {
                "mask_id": "adult_student_very_long_experience",
                "target": "experience",
                "condition": {"age": ["adult"], "employment": ["student"]},
                "bad_values": ["very long"],
                "bad_value_multiplier": 0,
            },
            {
                "mask_id": "soft_rule",
                "target": "experience",
                "condition": {"age": ["adult"]},
                "bad_values": ["long"],
                "bad_value_multiplier": 0.1,
            },
        ]
    }
    codes = np.asarray(
        [
            [0, 0, 0],
            [0, 0, 1],
            [0, 1, 2],
            [1, 0, 2],
            [1, 1, 2],
        ],
        dtype=np.uint8,
    )

    rules = compile_hard_rules(graph, columns)
    rejected, counts = evaluate_hard_conflicts(codes, rules)

    assert [rule.rule_id for rule in rules] == [
        "minor_long_experience",
        "adult_student_very_long_experience",
    ]
    assert rejected.tolist() == [False, True, True, True, False]
    assert counts == {
        "minor_long_experience": 2,
        "adult_student_very_long_experience": 1,
    }