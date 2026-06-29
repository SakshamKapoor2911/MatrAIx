import json

import pytest
import yaml

from backend.service.harbor_survey_eval import (
    HarborSurveyEvalConfig,
    HarborSurveyEvalRunner,
    SurveyInstrument,
    SurveyQuestion,
    build_result_from_harbor_survey_artifacts,
    build_survey_task_prompt,
)
from persona_eval.types import Persona


def _instrument() -> SurveyInstrument:
    return SurveyInstrument(
        id="product_attitudes_v1",
        title="Product Attitudes",
        description="A short product concept survey.",
        questions=[
            SurveyQuestion(
                id="concept_fit",
                prompt="This product would fit my needs.",
                type="likert",
                min_value=1,
                max_value=5,
                construct="product_need_fit",
            ),
            SurveyQuestion(
                id="adoption_barrier",
                prompt="What would be your biggest barrier?",
                type="single_choice",
                options=["price", "privacy", "complexity"],
                construct="adoption_barrier",
            ),
        ],
    )


def _survey_payload() -> dict:
    return {
        "instrument": {
            "id": "product_attitudes_v1",
            "title": "Product Attitudes",
        },
        "answers": [
            {
                "questionId": "concept_fit",
                "value": 4,
                "rationale": "The persona is pragmatic but sees a clear use case.",
                "confidence": 0.8,
            },
            {
                "questionId": "adoption_barrier",
                "value": "privacy",
                "rationale": "The persona tends to be cautious about data sharing.",
                "confidence": 0.7,
            },
        ],
        "trajectory": [
            {
                "timestamp": "2026-06-24T00:00:00Z",
                "actor": "system",
                "action": "survey_started",
                "context": {
                    "personaId": "p1",
                    "instrumentId": "product_attitudes_v1",
                },
                "outcome": {},
            },
            {
                "timestamp": "2026-06-24T00:00:01Z",
                "actor": "assistant",
                "action": "ask_question",
                "context": {
                    "questionId": "concept_fit",
                    "construct": "product_need_fit",
                },
                "outcome": {},
            },
            {
                "timestamp": "2026-06-24T00:00:02Z",
                "actor": "user",
                "action": "answer_question",
                "context": {
                    "questionId": "concept_fit",
                    "construct": "product_need_fit",
                },
                "outcome": {
                    "questionId": "concept_fit",
                    "value": 4,
                    "rationale": "The persona is pragmatic but sees a clear use case.",
                    "confidence": 0.8,
                },
            },
            {
                "timestamp": "2026-06-24T00:00:03Z",
                "actor": "assistant",
                "action": "ask_question",
                "context": {
                    "questionId": "adoption_barrier",
                    "construct": "adoption_barrier",
                },
                "outcome": {},
            },
            {
                "timestamp": "2026-06-24T00:00:04Z",
                "actor": "user",
                "action": "answer_question",
                "context": {
                    "questionId": "adoption_barrier",
                    "construct": "adoption_barrier",
                },
                "outcome": {
                    "questionId": "adoption_barrier",
                    "value": "privacy",
                    "rationale": "The persona tends to be cautious about data sharing.",
                    "confidence": 0.7,
                },
            },
            {
                "timestamp": "2026-06-24T00:00:05Z",
                "actor": "system",
                "action": "survey_completed",
                "context": {
                    "personaId": "p1",
                    "instrumentId": "product_attitudes_v1",
                },
                "outcome": {"numAnswered": 2},
            },
        ],
    }


def test_build_survey_task_prompt_uses_persona_prompt_and_trajectory_schema():
    prompt = build_survey_task_prompt(instrument=_instrument())

    assert "Harbor supplies the persona system prompt" in prompt
    assert "Product concept being evaluated" in prompt
    assert "PersonaEval" in prompt
    assert "product_attitudes_v1" in prompt
    assert "/app/output/survey_result.json" in prompt
    assert '"trajectory"' in prompt
    assert '"timestamp"' in prompt
    assert '"actor"' in prompt
    assert '"action"' in prompt
    assert '"context"' in prompt
    assert '"outcome"' in prompt


def test_build_result_from_harbor_survey_artifacts_maps_answers_trajectory_and_metrics(
    tmp_path,
):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "survey_result.json").write_text(
        json.dumps(_survey_payload()),
        encoding="utf-8",
    )

    result = build_result_from_harbor_survey_artifacts(
        output_dir=output_dir,
        config=HarborSurveyEvalConfig(persona_model="anthropic/claude-sonnet-4-6"),
        persona=Persona(id="p1", name="Persona One", context="Careful respondent."),
        instrument=_instrument(),
        created_at="2026-06-24T00:00:00Z",
        prompts={
            "harborPrompt": "Careful respondent.",
            "taskPrompt": "Survey task prompt.",
        },
    )

    payload = result.to_dict()
    assert payload["config"]["personaModel"] == "anthropic/claude-sonnet-4-6"
    assert payload["instrument"]["id"] == "product_attitudes_v1"
    assert payload["answers"][0]["value"] == 4
    assert payload["answers"][1]["value"] == "privacy"
    assert payload["metrics"] == {
        "numQuestions": 2,
        "numAnswered": 2,
        "meanLikert": 4.0,
    }
    assert payload["prompts"] == {
        "harborPrompt": "Careful respondent.",
        "taskPrompt": "Survey task prompt.",
    }


def test_build_result_from_harbor_survey_artifacts_rejects_bad_trajectory(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    payload = _survey_payload()
    payload["trajectory"][0].pop("outcome")
    (output_dir / "survey_result.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="trajectory event missing"):
        build_result_from_harbor_survey_artifacts(
            output_dir=output_dir,
            config=HarborSurveyEvalConfig(),
            persona=Persona(id="p1", name="Persona One"),
            instrument=_instrument(),
            created_at="2026-06-24T00:00:00Z",
        )


def test_harbor_survey_runner_uses_persona_survey_task(tmp_path):
    calls = []
    (tmp_path / ".env.local").write_text(
        "ANTHROPIC_API_KEY=sk-test-anthropic\n",
        encoding="utf-8",
    )

    def fake_command(command, *, cwd, env):
        calls.append((command, cwd, env))
        config_path = command[command.index("-c") + 1]
        config = yaml.safe_load(open(config_path, encoding="utf-8"))
        assert config["agents"][0]["name"] == "persona-claude-code"
        assert config["agents"][0]["model_name"] == "anthropic/claude-sonnet-4-6"
        assert config["tasks"][0]["path"].endswith("application/tasks/persona-survey")
        assert config["environment"]["type"] == "docker"
        assert config["environment"]["force_build"] is False
        prompt_text = open(config["extra_instruction_paths"][0], encoding="utf-8").read()
        assert "product_attitudes_v1" in prompt_text
        assert env["MATRIX_SURVEY_INSTRUMENT_ID"] == "product_attitudes_v1"
        assert env["ANTHROPIC_API_KEY"] == "sk-test-anthropic"

        output_dir = (
            tmp_path
            / "runs"
            / config["job_name"]
            / "survey_form__fake"
            / "artifacts"
            / "app"
            / "output"
        )
        output_dir.mkdir(parents=True)
        (output_dir / "survey_result.json").write_text(
            json.dumps(_survey_payload()),
            encoding="utf-8",
        )
        return 0

    runner = HarborSurveyEvalRunner(
        repo_root=tmp_path,
        runs_root=tmp_path / "runs",
        command_runner=fake_command,
        harbor_command=("uv", "run", "--frozen", "harbor", "run"),
    )

    result = runner(
        Persona(id="p1", name="Persona One", context="Careful respondent."),
        _instrument(),
        HarborSurveyEvalConfig(persona_model="anthropic/claude-sonnet-4-6"),
        created_at="2026-06-24T00:00:00Z",
    )

    assert calls
    assert result.to_dict()["answers"][0]["questionId"] == "concept_fit"
