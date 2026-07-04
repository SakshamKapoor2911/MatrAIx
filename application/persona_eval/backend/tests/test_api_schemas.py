from backend.api.schemas import HarborJobLaunchRequest, StartPersonaEvalRequest


def test_start_persona_eval_request_prefers_application_context_for_recai():
    request = StartPersonaEvalRequest(
        applicationId="recai",
        applicationContext="beauty_product",
        personaId="p1",
    )

    assert request.applicationContext == "beauty_product"
    assert request.domain == "beauty_product"


def test_start_persona_eval_request_defaults_non_recai_context_and_clears_domain_role():
    request = StartPersonaEvalRequest(
        applicationId="medical_assistant",
        personaId="p1",
    )

    assert request.applicationContext == "medical_consultation"
    assert request.domain == "medical_consultation"


def test_harbor_job_launch_request_prefers_chat_application_context_for_recai():
    request = HarborJobLaunchRequest(
        taskPath="application/tasks/recommender-agent_chat_api",
        chatApplicationId="recai",
        chatApplicationContext="game",
    )

    assert request.chatApplicationContext == "game"
    assert request.chatDomain == "game"


def test_harbor_job_launch_request_defaults_non_recai_chat_context():
    request = HarborJobLaunchRequest(
        taskPath="application/tasks/medical-assistant_chatbot",
        chatApplicationId="medical_assistant",
    )

    assert request.chatApplicationContext == "medical_consultation"
    assert request.chatDomain is None
