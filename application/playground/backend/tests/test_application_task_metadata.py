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
    assert title_from_harbor_task_name("application/chat-recai") == "Chat Recai"
    assert (
        title_from_harbor_task_name("application/chat-multi-agent-medical-assistant")
        == "Chat Multi Agent Medical Assistant"
    )
    assert title_from_harbor_task_name("application/chat-openbb") == "Chat Openbb"
    # Legacy Harbor names still parse.
    assert (
        title_from_harbor_task_name("matraix/application-chat-recai")
        == "Chat Recai"
    )
