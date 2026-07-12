from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

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
        "YearsCode - Total coding years: 10", chunk, 2025
    )

    assert 'evidence of 10 maps to "6-10", not "11-20"' in prompt
    assert 'evidence of 11 maps to "11-20", not "6-10"' in prompt
    assert "choose the field whose question best matches the dimension" in prompt
    assert "Never move a numeric answer into an adjacent range" in prompt
    assert "the specific numeric answer used to support" in prompt
    assert "falls within the selected allowed-value range" in prompt


def test_prompt_uses_leak_safe_evidence_formats(extractor_module):
    chunk = extractor_module.DimensionChunk(
        chunk_id="evidence_test",
        label="Evidence test",
        description="Test evidence guidance.",
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
        "YearsCode - Total coding years: 10", chunk, 2023
    )

    assert "TechEndorse_1 - What attracts you" not in prompt
    assert "<ORIGINAL_COLUMN_NAME> - <READABLE_QUESTION_OR_SUBITEM>" in prompt
    assert "Evidence may be a short source quote or a faithful summary" in prompt
    assert "Prompt instructions, format templates" in prompt


def test_prompt_rank_guidance_is_year_specific_and_semantic(extractor_module):
    chunk = extractor_module.DimensionChunk(
        chunk_id="rank_test",
        label="Rank test",
        description="Test rank guidance.",
        source_categories=("Developer: Code Maintenance",),
        dimensions=(
            {
                "id": "debugging_strategy",
                "label": "Debugging strategy",
                "description": "Dominant debugging approach.",
                "values": ["Read code / traces first", "Interactive debugger"],
            },
        ),
    )

    prompt_2024 = extractor_module.build_stackoverflow_prompt(
        "JobSatPoints_1 - Driving strategy for my team: 20", chunk, 2024
    )
    prompt_2025 = extractor_module.build_stackoverflow_prompt(
        "SO_Actions_4 - Directly open a Q&A post via search: 1", chunk, 2025
    )

    assert "JobSatPoints_* values are allocated points, not ordinal ranks" in prompt_2024
    assert "TechEndorse answer is a select-all response" in prompt_2024
    assert "TechEndorse_*, JobSatPoints_*, and SO_Actions_* are ordinal ranks" in prompt_2025
    assert "ranked options themselves are those behaviors or strategies" in prompt_2025
    assert "Topical association alone is insufficient" in prompt_2025


def test_prompt_restores_high_precision_sparse_policy(extractor_module):
    chunk = extractor_module.DimensionChunk(
        chunk_id="precision_test",
        label="Precision test",
        description="Test conservative source-to-target guidance.",
        source_categories=("Skills: Professional",),
        dimensions=(
            {
                "id": "skill_debugging",
                "label": "Debugging skill",
                "description": "Demonstrated debugging proficiency.",
                "values": ["None", "Beginner", "Intermediate", "Advanced", "Master"],
            },
        ),
    )

    prompt = extractor_module.build_stackoverflow_prompt(
        "AIToolPlan to partially use AI - Planned AI tasks: Debugging", chunk, 2025
    )

    assert "Default decision: OMIT" in prompt
    assert "An empty fields list is a correct result" in prompt
    assert "Multiple weak proxies do not become strong evidence" in prompt
    assert "Do not reuse one broad answer to fan out" in prompt
    assert "summary_inference: a plausible, non-sensitive persona completion" in prompt
    assert "One strong source answer may support summary_inference" in prompt
    assert "non-normalized evidence-compatibility score" in prompt
    assert "Multiple mutually exclusive values may each be highly compatible" in prompt
    assert "High confidence requires positive, dimension-relevant evidence" in prompt
    assert "Mere absence of contradiction is not positive support" in prompt
    assert 'AISelect="No" narrows coding-AI usage away from Daily or Weekly' in prompt
    assert "not a fallback for missing evidence" in prompt
    assert "Task use is not task mastery" in prompt
    assert "valid supporting evidence for a specific-skill summary_inference" in prompt
    assert "do not automatically assign Advanced or Master across unrelated skills" in prompt


def test_prompt_blocks_observed_proxy_failure_modes(extractor_module):
    chunk = extractor_module.DimensionChunk(
        chunk_id="proxy_test",
        label="Proxy test",
        description="Test observed semantic overreach guidance.",
        source_categories=("Demographic: Core",),
        dimensions=(
            {
                "id": "primary_language",
                "label": "Primary language",
                "description": "Respondent's primary language.",
                "values": ["English", "Other"],
            },
        ),
    )

    prompt = extractor_module.build_stackoverflow_prompt(
        "Country - Where do you live?: Netherlands", chunk, 2025
    )

    assert "Intent is not experience" in prompt
    assert "Absence of evidence is not negative evidence" in prompt
    assert "Country may support region only" in prompt
    assert "no-current-AI-use answer directly constrains overall coding-AI usage" in prompt
    assert 'coding_ai_usage_frequency="Never used" or "Tried but not active"' in prompt
    assert "does not by itself constrain the history of every named AI product" in prompt
    assert 'company_size="Solo / freelance"' in prompt
    assert "does not establish founder status" in prompt
    assert "Compensation is individual compensation, not household income" in prompt
    assert "generic dependents answer" in prompt
    assert "work environment or exposure" in prompt
    assert "contribute to a personal-practice summary_inference" in prompt
    assert "organization-level evidence alone" in prompt
    assert "Technology choices and professional roles may support tool exposure and role facts" in prompt
    assert "people-manager or executive answer is strong evidence" in prompt
    assert "may support a skill_people_management or skill_leadership summary_inference" in prompt
    assert "Do not automatically map the role alone to Master or Signature" in prompt
    assert "bucket crosses more than one allowed output range" in prompt


@pytest.mark.parametrize("evidence", ["10", "8.5", "20%", "Yes", "No", "Employed"])
def test_validator_rejects_bare_evidence_values(extractor_module, evidence):
    chunk = extractor_module.DimensionChunk(
        chunk_id="bare_evidence_test",
        label="Bare evidence test",
        description="Test bare evidence rejection.",
        source_categories=("Professional: Career",),
        dimensions=(
            {
                "id": "years_experience",
                "label": "Years experience",
                "description": "Tenure in their field.",
                "values": ["6-10"],
            },
        ),
    )
    field = {
        "field_id": "years_experience",
        "value": "6-10",
        "confidence": 0.9,
        "evidence": evidence,
        "assignment_type": "direct",
    }

    with pytest.raises(ValueError, match="must include source context"):
        extractor_module.validate_chunk_payload({"fields": [field]}, chunk)


def evidence_test_chunk(extractor_module):
    return extractor_module.DimensionChunk(
        chunk_id="provenance_test",
        label="Provenance test",
        description="Test evidence provenance.",
        source_categories=("Professional: Career",),
        dimensions=(
            {
                "id": "years_experience",
                "label": "Years experience",
                "description": "Tenure in their field.",
                "values": ["6-10"],
            },
        ),
    )


def evidence_test_field(evidence, *, assignment_type="direct", confidence=0.9):
    return {
        "field_id": "years_experience",
        "value": "6-10",
        "confidence": confidence,
        "evidence": evidence,
        "assignment_type": assignment_type,
    }


def test_validator_accepts_current_source_quote_and_summary(extractor_module):
    chunk = evidence_test_chunk(extractor_module)
    sources = {"YearsCode": "10", "DevType": "Developer;Researcher"}
    direct = evidence_test_field("YearsCode - Total coding years: 10")
    summary = evidence_test_field(
        "YearsCode=10; DevType=Developer. Summary: ten years of coding experience",
        assignment_type="summary_inference",
        confidence=0.85,
    )

    assert extractor_module.validate_chunk_payload(
        {"fields": [direct]}, chunk, sources
    ) == [direct]
    assert extractor_module.validate_chunk_payload(
        {"fields": [summary]}, chunk, sources
    ) == [summary]


@pytest.mark.parametrize(
    ("evidence", "sources"),
    [
        (
            "JobSatPoints_6 - Improving quality of code: 20. Summary: "
            "Quality is a strong professional priority.",
            {"JobSatPoints_6": "20"},
        ),
        (
            "YearsCode=10 (total coding years). Summary: The respondent has "
            "substantial coding experience.",
            {"YearsCode": "10"},
        ),
    ],
)
def test_validator_accepts_common_evidence_format_variants(
    extractor_module, evidence, sources
):
    chunk = evidence_test_chunk(extractor_module)
    field = evidence_test_field(evidence, assignment_type="summary_inference")

    assert extractor_module.validate_chunk_payload(
        {"fields": [field]}, chunk, sources
    ) == [field]


def test_validator_rejects_overlong_or_deliberative_evidence(extractor_module):
    chunk = evidence_test_chunk(extractor_module)
    overlong = evidence_test_field(
        "YearsCode=10. Summary: "
        + "x" * extractor_module.MAX_EVIDENCE_CHARS
    )
    deliberative = evidence_test_field(
        "YearsCode=10. Summary: Let's re-evaluate whether this should be omitted."
    )

    with pytest.raises(ValueError, match="must be no longer than"):
        extractor_module.validate_chunk_payload(
            {"fields": [overlong]}, chunk, {"YearsCode": "10"}
        )
    with pytest.raises(ValueError, match="contains model deliberation"):
        extractor_module.validate_chunk_payload(
            {"fields": [deliberative]}, chunk, {"YearsCode": "10"}
        )


def test_validator_accepts_single_source_summary_inference(extractor_module):
    chunk = evidence_test_chunk(extractor_module)
    one_source = evidence_test_field(
        "YearsCode - Total coding years: 10",
        assignment_type="summary_inference",
        confidence=0.85,
    )
    sources = {"YearsCode": "10"}

    assert extractor_module.validate_chunk_payload(
        {"fields": [one_source]}, chunk, sources
    ) == [one_source]


def test_zero_field_salvage_triggers_retry(extractor_module, monkeypatch):
    chunk = evidence_test_chunk(extractor_module)
    invalid_field = evidence_test_field("YearsCode - Total coding years: 11")
    valid_field = evidence_test_field("YearsCode - Total coding years: 10")

    def output_for(field):
        return SimpleNamespace(
            outputs=[
                SimpleNamespace(
                    text=json.dumps({"fields": [field]}),
                    finish_reason="stop",
                    stop_reason=None,
                )
            ]
        )

    retry_calls = []

    def fake_run_chat(llm, conversations, sampling):
        retry_calls.append(conversations)
        return [output_for(valid_field)]

    monkeypatch.setattr(extractor_module, "run_chat", fake_run_chat)

    fields = extractor_module.parse_generation_with_retry(
        llm=object(),
        sampling=object(),
        chunk=chunk,
        conversation=[{"role": "user", "content": "test prompt"}],
        initial_output=output_for(invalid_field),
        year=2024,
        row_index=0,
        source_answers={"YearsCode": "10"},
    )

    assert fields == [valid_field]
    assert len(retry_calls) == 1


def test_validator_rejects_source_absent_from_current_profile(extractor_module):
    chunk = evidence_test_chunk(extractor_module)
    field = evidence_test_field(
        "TechEndorse_1 - AI integration or AI Agent capabilities: 10"
    )

    with pytest.raises(ValueError, match="absent from the current respondent profile"):
        extractor_module.validate_chunk_payload(
            {"fields": [field]}, chunk, {"YearsCode": "10"}
        )


def test_validator_rejects_answer_mismatched_to_current_respondent(extractor_module):
    chunk = evidence_test_chunk(extractor_module)
    field = evidence_test_field("YearsCode - Total coding years: 11")

    with pytest.raises(ValueError, match="without its current respondent answer"):
        extractor_module.validate_chunk_payload(
            {"fields": [field]}, chunk, {"YearsCode": "10"}
        )


def test_question_numbers_do_not_mask_a_mismatched_answer(extractor_module):
    chunk = evidence_test_chunk(extractor_module)
    field = evidence_test_field(
        "JobSatPoints_1 - Rank from 1 (most important) to 10: 4"
    )

    with pytest.raises(ValueError, match="without its current respondent answer"):
        extractor_module.validate_chunk_payload(
            {"fields": [field]}, chunk, {"JobSatPoints_1": "1"}
        )


def test_validator_rejects_summary_without_explicit_source_column(extractor_module):
    chunk = evidence_test_chunk(extractor_module)
    field = evidence_test_field("The respondent reports ten years of experience.")

    with pytest.raises(ValueError, match="must cite at least one"):
        extractor_module.validate_chunk_payload(
            {"fields": [field]}, chunk, {"YearsCode": "10"}
        )


def test_visible_profile_sources_exclude_truncated_rows(extractor_module):
    row = {"YearsCode": "10", "DevType": "Developer"}
    profile = "Profile header\n\n## Career\n- YearsCode - Total coding years: 10"

    assert extractor_module.visible_profile_source_answers(row, profile) == {
        "YearsCode": "10"
    }


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


