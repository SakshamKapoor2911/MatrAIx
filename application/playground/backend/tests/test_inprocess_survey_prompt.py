from pathlib import Path

from backend.service.example_task_catalog import repo_root
from backend.service.survey_questionnaire_catalog import get_survey_questionnaire
from backend.service.survey_types import SurveyEvalConfig, SurveyInstrument, SurveyQuestion
from playground.inprocess.survey_eval import (
    InprocessSurveyEvalRunner,
    build_survey_task_prompt,
    persona_system_prompt,
)
from playground.types import Persona


def _write_dims_yaml(path: Path, *, persona_id: str, **dims: str) -> Path:
    lines = [
        f"persona_id: '{persona_id}'",
        "version: '1.0'",
        "dimensions:",
    ]
    for key, value in dims.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def test_repo_backed_local_survey_prompt_is_only_document_bundle():
    instrument = get_survey_questionnaire("product_attitudes_v1", repo_root=repo_root())

    prompt = build_survey_task_prompt(instrument=instrument)

    assert "You are completing a market research survey" not in prompt
    assert "The persona is provided separately in the system prompt." not in prompt
    assert "Additional answer rule:" not in prompt
    assert "## Task instruction" in prompt
    assert "## Context" in prompt
    assert "## Questionnaire" in prompt
    assert "## Answer envelope" in prompt
    assert "## Output schema" not in prompt
    assert "input/output_schema.md" not in prompt


def test_unmapped_local_survey_prompt_falls_back_to_rendered_docs_only():
    instrument = SurveyInstrument(
        id="survey1",
        title="Survey",
        description="A survey about a concrete feature.",
        questions=[SurveyQuestion(id="fit", prompt="This fits me.")],
    )

    prompt = build_survey_task_prompt(instrument=instrument)

    assert "You are completing a market research survey" not in prompt
    assert "The persona is provided separately in the system prompt." not in prompt
    assert "## Task instruction" in prompt
    assert "## Context" in prompt
    assert "## Questionnaire" in prompt
    assert "## Answer envelope" in prompt
    assert "## Output schema" not in prompt
    assert "A survey about a concrete feature." in prompt
    assert "Ask rationale:" not in prompt
    assert "Ask confidence:" not in prompt
    assert "selected value only" in prompt
    assert "questionId` + `value` only" in prompt


def test_persona_system_prompt_renders_dimensions_yaml(tmp_path: Path):
    yaml_path = _write_dims_yaml(
        tmp_path / "persona_0902.yaml",
        persona_id="0902",
        age_bracket="65+",
        region="South Asia",
        gender_identity="Woman",
        socioeconomic_band="Middle",
        life_stage="Retirement",
    )
    persona = Persona(id="0902", name="persona-0902")

    prompt = persona_system_prompt(persona, persona_yaml_path=str(yaml_path))

    assert "## Persona" in prompt
    assert "Who you are" in prompt or "Simulated person: 0902" in prompt
    assert "65" in prompt or "South Asia" in prompt or "Retirement" in prompt


def test_survey_runner_requires_yaml_path_for_persona_prompt(monkeypatch, tmp_path: Path):
    yaml_path = _write_dims_yaml(
        tmp_path / "persona_dims.yaml",
        persona_id="0042",
        age_bracket="25-34",
        region="North America",
        gender_identity="Man",
    )

    class FakeJSONClient:
        def complete_json(self, system, user):
            return {
                "answers": [
                    {
                        "questionId": "fit",
                        "value": 4,
                        "rationale": "Fits.",
                        "confidence": 0.8,
                    }
                ]
            }

    monkeypatch.setattr(
        "playground.inprocess.survey_eval.build_json_client",
        lambda model: FakeJSONClient(),
    )
    persona = Persona(id="0042", name="persona-0042")
    instrument = SurveyInstrument(
        id="survey1",
        title="Survey",
        questions=[SurveyQuestion(id="fit", prompt="This fits me.")],
    )

    result = InprocessSurveyEvalRunner()(
        persona,
        instrument,
        SurveyEvalConfig(persona_model="openai/gpt-4o-mini"),
        created_at="2026-06-26T00:00:00Z",
        persona_yaml_path=str(yaml_path),
    )

    assert "Who you are" in result.prompts["personaPrompt"] or "25-34" in result.prompts[
        "personaPrompt"
    ]
