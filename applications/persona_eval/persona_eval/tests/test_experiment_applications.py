from persona_eval.experiments.applications import (
    build_chatbot_task_prompt,
    list_application_specs,
    parse_application_ref,
)


def test_application_registry_covers_chatbot_targets():
    apps = {app.key: app for app in list_application_specs()}

    assert set(apps) == {
        "recai:movie",
        "recai:beauty_product",
        "recai:game",
        "finance_openbb:financial_research",
        "medical_assistant:medical_consultation",
    }
    assert apps["recai:movie"].concurrency_limit == 1
    assert apps["finance_openbb:financial_research"].concurrency_limit > 1


def test_parse_application_ref_accepts_short_aliases():
    assert parse_application_ref("movie").key == "recai:movie"
    assert parse_application_ref("recai/game").key == "recai:game"
    assert parse_application_ref("finance").application_id == "finance_openbb"
    assert parse_application_ref("medical").application_context == "medical_consultation"


def test_chatbot_task_prompt_is_application_specific():
    prompt = build_chatbot_task_prompt(parse_application_ref("finance"))

    assert "financial research system" in prompt
    assert "OpenBB data tools" in prompt
    assert "assigned persona" in prompt
    assert "Do not reveal everything at once" in prompt
