from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).with_name("extract_personas_stackoverflow_vllm_v2.py")


@pytest.fixture(scope="module")
def extractor_module():
    spec = importlib.util.spec_from_file_location(
        "stackoverflow_vllm_v2_test", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def mapping_for(*columns: str) -> dict[str, dict[str, str]]:
    return {
        column: {
            "description": f"Readable question | Response column: {column}",
        }
        for column in columns
    }


def fields_by_id(fields):
    return {field["field_id"]: field for field in fields}


def test_2025_ai_task_statuses_are_mapped_deterministically(extractor_module):
    row = {
        "AIToolCurrently partially AI": "Writing code;Learning about a codebase",
        "AIToolPlan to partially use AI": "Debugging or fixing code;Testing code",
        "AIToolPlan to mostly use AI": "Committing and reviewing code",
        "AIToolDon't plan to use AI for this task": "Project planning",
    }
    fields = fields_by_id(
        extractor_module.extract_2025_ai_task_fields(
            row, 2025, mapping_for(*row)
        )
    )

    assert fields["ai_task_code_generation"]["value"] == (
        "Currently partially AI-assisted"
    )
    assert fields["ai_task_codebase_learning"]["value"] == (
        "Currently partially AI-assisted"
    )
    assert fields["ai_task_debugging_fixing"]["value"] == "Plans partial AI use"
    assert fields["ai_task_testing"]["value"] == "Plans partial AI use"
    assert fields["ai_task_code_review"]["value"] == "Plans mostly AI use"
    assert fields["ai_task_project_planning"]["value"] == "Does not plan AI use"
    assert all(field["assignment_type"] == "direct" for field in fields.values())
    assert all(field["confidence"] == 1.0 for field in fields.values())


def test_2025_aggregated_tasks_use_strongest_current_status(extractor_module):
    row = {
        "AIToolCurrently partially AI": "Documenting code",
        "AIToolPlan to mostly use AI": (
            "Creating or maintaining documentation;Predictive analytics"
        ),
        "AIToolPlan to partially use AI": "Generating content or synthetic data",
    }
    fields = fields_by_id(
        extractor_module.extract_2025_ai_task_fields(
            row, 2025, mapping_for(*row)
        )
    )

    documentation = fields["ai_task_documentation"]
    assert documentation["value"] == "Currently partially AI-assisted"
    assert "Documenting code" in documentation["evidence"]
    assert "Creating or maintaining documentation" in documentation["evidence"]

    data_generation = fields["ai_task_data_generation_analytics"]
    assert data_generation["value"] == "Plans mostly AI use"
    assert "Predictive analytics" in data_generation["evidence"]
    assert "Generating content or synthetic data" in data_generation["evidence"]


@pytest.mark.parametrize("year", [2023, 2024])
def test_2025_ai_task_crosswalk_is_year_isolated(extractor_module, year):
    row = {"AIToolPlan to partially use AI": "Testing code"}

    assert extractor_module.extract_2025_ai_task_fields(
        row, year, mapping_for(*row)
    ) == []


def test_deterministic_fields_replace_model_values(extractor_module):
    generated = [
        {
            "field_id": "age_bracket",
            "value": "25-34",
            "confidence": 1.0,
            "evidence": "Age: 25-34 years old",
            "assignment_type": "direct",
        },
        {
            "field_id": "ai_task_testing",
            "value": "Currently partially AI-assisted",
            "confidence": 1.0,
            "evidence": "incorrect model mapping",
            "assignment_type": "direct",
        },
    ]
    deterministic = [
        {
            "field_id": "ai_task_testing",
            "value": "Plans partial AI use",
            "confidence": 1.0,
            "evidence": "AIToolPlan to partially use AI: Testing code",
            "assignment_type": "direct",
        }
    ]

    result = extractor_module.overlay_deterministic_fields(
        generated,
        deterministic,
        extractor_module.STACKOVERFLOW_2025_AI_TASK_FIELD_IDS,
    )

    assert fields_by_id(result) == {
        "age_bracket": generated[0],
        "ai_task_testing": deterministic[0],
    }


def test_prompt_requires_numeric_evidence_range_consistency(extractor_module):
    chunk = extractor_module.DimensionChunk(
        chunk_id="experience_test",
        label="Experience test",
        description="Test numeric range guidance.",
        source_categories=("Professional: Career",),
        dimensions=(
            {
                "id": "years_experience",
                "label": "Years experience",
                "description": "Tenure in their field.",
                "values": ["0-2", "3-5", "6-10", "11-20", "20+"],
            },
        ),
    )

    prompt = extractor_module.build_stackoverflow_prompt(
        "YearsCode - Total coding years: 10", chunk
    )

    assert 'evidence of 10 maps to "6-10", not "11-20"' in prompt
    assert 'evidence of 11 maps to "11-20", not "6-10"' in prompt
    assert "choose the field whose question best matches the dimension" in prompt
    assert "Never move a numeric answer into an adjacent range" in prompt
    assert "the specific numeric answer used to support" in prompt
    assert "falls within the selected allowed-value range" in prompt


def test_unsupported_assignment_is_accepted_then_dropped(extractor_module):
    chunk = extractor_module.DimensionChunk(
        chunk_id="unsupported_test",
        label="Unsupported test",
        description="Test unsupported output rejection.",
        source_categories=("Professional: Career",),
        dimensions=(
            {
                "id": "years_experience",
                "label": "Years experience",
                "description": "Tenure in their field.",
                "values": ["0-2", "3-5", "6-10", "11-20", "20+"],
            },
        ),
    )
    unsupported = {
        "field_id": "years_experience",
        "value": "6-10",
        "confidence": 0.9,
        "evidence": "No supporting evidence",
        "assignment_type": "unsupported",
    }

    schema = extractor_module.build_chunk_json_schema(chunk)
    assignment_enum = schema["properties"]["fields"]["items"]["oneOf"][0][
        "properties"
    ]["assignment_type"]["enum"]
    assert "unsupported" in assignment_enum
    assert extractor_module.validate_chunk_payload(
        {"fields": [unsupported]}, chunk
    ) == [unsupported]

    supported = {**unsupported, "assignment_type": "direct"}
    assert extractor_module.drop_unsupported_fields([unsupported, supported]) == [
        supported
    ]


