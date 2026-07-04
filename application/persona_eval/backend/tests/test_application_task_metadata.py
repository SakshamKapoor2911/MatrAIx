from backend.service.application_task_metadata import title_from_harbor_task_name


def test_title_from_harbor_task_name():
    assert (
        title_from_harbor_task_name("personabench/application-web-playwright-quote-choice")
        == "Web Playwright Quote Choice"
    )
    assert (
        title_from_harbor_task_name("personabench/application-survey-nike-air-max-dn")
        == "Survey Nike Air Max Dn"
    )
    assert (
        title_from_harbor_task_name("personabench/application-survey-product-feedback")
        == "Survey Product Feedback"
    )
