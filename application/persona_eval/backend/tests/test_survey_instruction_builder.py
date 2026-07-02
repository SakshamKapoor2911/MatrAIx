from backend.service.survey_instruction_builder import render_survey_instruction_markdown
from backend.service.survey_instruments import get_survey_instrument


def test_render_survey_instruction_includes_context_and_questions():
    instrument = get_survey_instrument("commerce_nike_air_max_dn_dynamic_air_v1")
    markdown = render_survey_instruction_markdown(instrument)
    assert "# Nike Air Max Dn" in markdown
    assert "## Context" in markdown
    assert "Dynamic Air" in markdown
    assert "### dynamic_air_appeal" in markdown
    assert "survey_result.json" in markdown
