from __future__ import annotations

import json

from persona_eval.experiments.applications import parse_application_ref
from persona_eval.experiments.batch import build_run_specs
from persona_eval.experiments.web import WebExperimentRunner
from persona_eval.types import Persona


class FakeWebPersonaModel:
    def complete_web_task(self, request):
        product = request["catalog"]["products"][0]
        return {
            "task_statement": "I want to find a practical home product that fits my persona.",
            "selected_product_id": product["id"],
            "selected_product_name": product["name"],
            "need_satisfaction": 8,
            "ease_of_use": 7,
            "overall_experience_rating": 8,
            "reason": "The website made it easy to compare product summaries and choose a suitable option.",
            "trace": [
                {
                    "step": 1,
                    "action": "inspect_catalog",
                    "observation": "Reviewed available product cards.",
                },
                {
                    "step": 2,
                    "action": "select_product",
                    "observation": product["id"],
                },
            ],
        }


def test_web_experiment_runner_writes_result_and_trace(tmp_path):
    persona = Persona(id="p1", name="Persona One", context="Practical apartment renter.")
    application = parse_application_ref("web")
    spec = build_run_specs(
        personas=[persona],
        applications=[application],
        api_url="unused",
        persona_model="fake-persona",
        max_turns=1,
        min_turns=1,
        goal_context_id="scenario_default",
    )[0]
    runner = WebExperimentRunner(
        persona_model_factory=lambda _spec, _persona: FakeWebPersonaModel(),
        now=lambda: "2026-06-26T00:00:00Z",
    )

    result = runner.run(spec, persona, tmp_path / "run", application)

    assert result.status == "done"
    assert "ecommerce_interaction.json" in result.artifacts
    assert "web_trace.json" in result.artifacts
    assert "experiment_run.json" in result.artifacts
    web_result = json.loads((tmp_path / "run" / "ecommerce_interaction.json").read_text())
    assert web_result["selected_product_id"]
    trace = json.loads((tmp_path / "run" / "web_trace.json").read_text())
    assert len(trace["events"]) == 2
