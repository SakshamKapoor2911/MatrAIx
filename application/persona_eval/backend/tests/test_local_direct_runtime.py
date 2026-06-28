from backend.api.deps import (
    build_persona_eval_service,
    build_survey_eval_service,
    build_web_eval_service,
)
from backend.service.catalog_index import CatalogIndex
from backend.service.config import ConfigManager


def test_default_eval_services_use_local_runners():
    """PersonaEval's default UI runtime should use direct local runners."""
    chatbot = build_persona_eval_service(CatalogIndex(None), ConfigManager())
    survey = build_survey_eval_service()
    web = build_web_eval_service()

    assert chatbot._runner.__class__.__name__ == "LocalChatbotEvalRunner"
    assert survey._runner.__class__.__name__ == "LocalSurveyEvalRunner"
    assert web._runner.__class__.__name__ == "LocalWebEvalRunner"


def test_config_environment_describes_direct_local_runtime(config_manager):
    env = config_manager.options()["environment"]
    serialized = repr(env).lower()

    assert env["runtime"] == "Local direct runner"
    assert "harbor" not in serialized
    assert "docker" not in serialized
