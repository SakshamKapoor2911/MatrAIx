from backend.service.application_task_metadata import title_from_harbor_task_name


def test_title_from_harbor_task_name():
    assert (
        title_from_harbor_task_name("application/web-playwright-quote-choice")
        == "Web Playwright Quote Choice"
    )
    assert (
        title_from_harbor_task_name("application/survey-nike-air-max-dn")
        == "Survey Nike Air Max Dn"
    )
    assert (
        title_from_harbor_task_name("application/survey-product-feedback")
        == "Survey Product Feedback"
    )
    assert (
        title_from_harbor_task_name("application/recommender-agent-chat-api")
        == "Recommender Agent Chat Api"
    )
    assert (
        title_from_harbor_task_name("application/medical-assistant-chatbot")
        == "Medical Assistant Chatbot"
    )
    # Legacy Harbor names still parse.
    assert (
        title_from_harbor_task_name("personabench/application-recommender-agent-chat-api")
        == "Recommender Agent Chat Api"
    )
