from pathlib import Path

from persona_eval.experiments.applications import parse_application_ref
from persona_eval.experiments.models import ExperimentRunResult, ExperimentRunSpec
from persona_eval.experiments.suite import ExperimentApplicationRunner
from persona_eval.types import Persona


class FakeRunner:
    def __init__(self, status):
        self.status = status
        self.calls = []

    def run(self, spec, persona, output_dir, application):
        self.calls.append((spec, persona, output_dir, application))
        return ExperimentRunResult(
            run_id=spec.run_id,
            status=self.status,
            output_dir=output_dir,
            started_at="start",
            finished_at="finish",
        )


def _spec(application):
    return ExperimentRunSpec(
        run_id="run_1",
        persona_id="p1",
        application_key=application.key,
        application_type=application.application_type,
        application_id=application.application_id,
        application_context=application.application_context,
        domain=application.domain,
        api_url="http://fake.local",
        persona_model="fake-persona",
    )


def test_application_runner_dispatches_by_application_type(tmp_path):
    chatbot = FakeRunner("chatbot")
    survey = FakeRunner("survey")
    web = FakeRunner("web")
    runner = ExperimentApplicationRunner(
        chatbot_runner=chatbot,
        survey_runner=survey,
        web_runner=web,
    )
    persona = Persona(id="p1", name="Persona")

    for ref, expected in (
        ("movie", chatbot),
        ("survey", survey),
        ("web", web),
    ):
        application = parse_application_ref(ref)
        result = runner.run(_spec(application), persona, tmp_path / ref, application)
        assert result.status == expected.status
        assert len(expected.calls) == 1
        assert expected.calls[0][3] == application
