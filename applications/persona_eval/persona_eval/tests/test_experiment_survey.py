from __future__ import annotations

import json

from persona_eval.experiments.applications import parse_application_ref
from persona_eval.experiments.batch import build_run_specs
from persona_eval.experiments.survey import SurveyExperimentRunner
from persona_eval.types import Persona


class FakeSurveyPersonaModel:
    def complete_survey(self, request):
        questions = request["instrument"]["questions"]
        answers = []
        trajectory = [
            {
                "timestamp": "2026-06-26T00:00:00Z",
                "actor": "system",
                "action": "survey_started",
                "context": {"instrumentId": request["instrument"]["id"]},
                "outcome": {},
            }
        ]
        for question in questions:
            if question["type"] == "likert":
                value = question["maxValue"]
            elif question["type"] == "single_choice":
                value = question["options"][-1]
            elif question["type"] == "multi_choice":
                value = question["options"][:1]
            else:
                value = "This fits how I would evaluate the product."
            answers.append(
                {
                    "questionId": question["id"],
                    "value": value,
                    "rationale": "Persona-grounded reason.",
                    "confidence": 0.8,
                }
            )
            trajectory.append(
                {
                    "timestamp": "2026-06-26T00:00:01Z",
                    "actor": "user",
                    "action": "answer_question",
                    "context": {"questionId": question["id"]},
                    "outcome": {"questionId": question["id"], "value": value},
                }
            )
        trajectory.append(
            {
                "timestamp": "2026-06-26T00:00:02Z",
                "actor": "system",
                "action": "survey_completed",
                "context": {"instrumentId": request["instrument"]["id"]},
                "outcome": {"answers": len(answers)},
            }
        )
        return {
            "instrument": {
                "id": request["instrument"]["id"],
                "title": request["instrument"]["title"],
            },
            "answers": answers,
            "trajectory": trajectory,
        }


def test_survey_experiment_runner_writes_normalized_result(tmp_path):
    persona = Persona(id="p1", name="Persona One", context="Budget-conscious shopper.")
    application = parse_application_ref("survey")
    spec = build_run_specs(
        personas=[persona],
        applications=[application],
        api_url="unused",
        persona_model="fake-persona",
        max_turns=1,
        min_turns=1,
        goal_context_id="scenario_default",
    )[0]
    runner = SurveyExperimentRunner(
        persona_model_factory=lambda _spec, _persona: FakeSurveyPersonaModel(),
        now=lambda: "2026-06-26T00:00:00Z",
    )

    result = runner.run(spec, persona, tmp_path / "run", application)

    assert result.status == "done"
    assert "survey_result.json" in result.artifacts
    assert "events.ndjson" in result.artifacts
    assert "experiment_run.json" in result.artifacts
    survey = json.loads((tmp_path / "run" / "survey_result.json").read_text())
    assert survey["instrument"]["id"] == "product_attitudes_v1"
    assert len(survey["answers"]) == 5
    experiment = json.loads((tmp_path / "run" / "experiment_run.json").read_text())
    assert experiment["metadata"]["metrics"]["numAnswered"] == 5
