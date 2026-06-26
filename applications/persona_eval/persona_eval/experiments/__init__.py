"""Headless PersonaEval experiment runners.

The experiment package is intentionally independent from Harbor and the
PersonaEval frontend. It drives application adapters through the stable
task-owned contracts and writes auditable artifacts for paper experiments.
"""

from persona_eval.experiments.applications import (
    ApplicationSpec,
    get_application_spec,
    list_application_specs,
    parse_application_ref,
)
from persona_eval.experiments.batch import ExperimentBatchRunner, build_run_specs
from persona_eval.experiments.chatbot import ChatbotExperimentRunner
from persona_eval.experiments.models import ExperimentRunResult, ExperimentRunSpec

__all__ = [
    "ApplicationSpec",
    "ChatbotExperimentRunner",
    "ExperimentBatchRunner",
    "ExperimentRunResult",
    "ExperimentRunSpec",
    "build_run_specs",
    "get_application_spec",
    "list_application_specs",
    "parse_application_ref",
]
