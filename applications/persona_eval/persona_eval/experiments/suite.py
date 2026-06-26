from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from persona_eval.experiments.applications import ApplicationSpec
from persona_eval.experiments.chatbot import ChatbotExperimentRunner
from persona_eval.experiments.models import ExperimentRunResult, ExperimentRunSpec
from persona_eval.experiments.survey import SurveyExperimentRunner
from persona_eval.experiments.web import WebExperimentRunner
from persona_eval.types import Persona


class ExperimentApplicationRunner:
    """Dispatch one experiment run to the matching application-type runner."""

    def __init__(
        self,
        *,
        chatbot_runner: Optional[Any] = None,
        survey_runner: Optional[Any] = None,
        web_runner: Optional[Any] = None,
    ) -> None:
        self.chatbot_runner = chatbot_runner or ChatbotExperimentRunner()
        self.survey_runner = survey_runner or SurveyExperimentRunner(now=_utc_now)
        self.web_runner = web_runner or WebExperimentRunner(now=_utc_now)

    def run(
        self,
        spec: ExperimentRunSpec,
        persona: Persona,
        output_dir: Path,
        application: ApplicationSpec,
    ) -> ExperimentRunResult:
        if application.application_type == "chatbot":
            return self.chatbot_runner.run(spec, persona, output_dir, application)
        if application.application_type == "survey":
            return self.survey_runner.run(spec, persona, output_dir, application)
        if application.application_type == "web":
            return self.web_runner.run(spec, persona, output_dir, application)
        raise ValueError("unsupported application type: {}".format(application.application_type))


def _utc_now() -> str:
    from datetime import datetime

    return datetime.utcnow().isoformat() + "Z"
