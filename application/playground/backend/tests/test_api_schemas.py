from backend.api.schemas import HarborJobLaunchRequest


def test_harbor_job_launch_request_prefers_chat_application_context_for_recai():
    request = HarborJobLaunchRequest(
        taskPath="application/tasks/chat_recai",
        chatApplicationId="recai",
        chatApplicationContext="game",
    )

    assert request.chatApplicationContext == "game"
    assert request.chatDomain == "game"


def test_harbor_job_launch_request_defaults_non_recai_chat_context():
    request = HarborJobLaunchRequest(
        taskPath="application/tasks/chat_multi-agent-medical-assistant",
        chatApplicationId="medical_assistant",
    )

    assert request.chatApplicationContext == "medical_consultation"
    assert request.chatDomain is None
