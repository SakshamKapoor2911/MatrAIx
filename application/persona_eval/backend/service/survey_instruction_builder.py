"""Render survey markdown assets from a normalized task-backed questionnaire."""

from __future__ import annotations

from backend.service.survey_types import SurveyInstrument, SurveyQuestion, SurveyTaskContent


def _render_question(question: SurveyQuestion) -> list[str]:
    lines = ["## {}".format(question.id), ""]
    if question.prompt:
        lines.append("Prompt: {}".format(question.prompt))
        lines.append("")
    if question.construct:
        lines.append("- Construct: `{}`".format(question.construct))
    lines.append("- Type: `{}`".format(question.type))
    lines.append("- Required: `{}`".format("true" if question.required else "false"))
    if question.type == "likert":
        lines.append("- Scale: `{}`-`{}`".format(question.min_value, question.max_value))
    lines.append("")
    if question.type == "likert":
        lines.append(
            "Rate with an integer between **{}** and **{}**.".format(
                question.min_value,
                question.max_value,
            )
        )
        lines.append("")
    elif question.type == "single_choice":
        lines.append("| choice_id | label |")
        lines.append("|-----------|-------|")
        for option in question.option_details:
            lines.append("| `{}` | {} |".format(option.id, option.label or option.id))
        if not question.option_details:
            for option in question.options:
                lines.append("| `{}` | {} |".format(option, option))
    elif question.type == "multi_choice":
        lines.append("| choice_id | label |")
        lines.append("|-----------|-------|")
        for option in question.option_details:
            lines.append("| `{}` | {} |".format(option.id, option.label or option.id))
        if not question.option_details:
            for option in question.options:
                lines.append("| `{}` | {} |".format(option, option))
    elif question.type == "free_text":
        lines.append("Respond in a short free-text answer.")
    lines.append("")
    return lines


def render_survey_task_instruction_markdown(instrument: SurveyInstrument) -> str:
    del instrument
    return "\n".join(
        [
            "Complete the survey using the provided context and structured questionnaire.",
            "",
            "Return one JSON object that matches `input/output_schema.md`.",
            "",
            "Requirements:",
            "",
            "- Answer every required question in `input/questionnaire.yaml`.",
            "- Use exact `questionId` values from the questionnaire.",
            "- For choice questions, use the exact choice ids.",
            "- For likert questions, use an integer within the declared range.",
            "- Keep each `rationale` concise and specific to the selected answer.",
            "- Return only the JSON object.",
            "",
            "Write the final JSON artifact to `/app/output/survey_result.json`.",
        ]
    ).strip() + "\n"


def render_survey_context_markdown(instrument: SurveyInstrument) -> str:
    return (
        (instrument.description or "Complete each required question using the provided survey materials.").strip()
        + "\n"
    )


def render_survey_questionnaire_markdown(instrument: SurveyInstrument) -> str:
    lines = [
        "# {}".format(instrument.title),
        "",
        "Use exact `questionId` and valid choice ids.",
        "",
    ]
    for question in instrument.questions:
        lines.extend(_render_question(question))
    return "\n".join(lines).strip() + "\n"


def render_survey_output_schema_markdown(instrument: SurveyInstrument) -> str:
    example_question_id = instrument.questions[0].id if instrument.questions else "q1"
    return "\n".join(
        [
            "Return strict JSON matching this shape.",
            "",
            "```json",
            "{",
            '  "instrument": {"id": "%s", "title": "%s"},'
            % (instrument.id, instrument.title.replace('"', '\\"')),
            '  "answers": [',
            "    {",
            '      "questionId": "%s",' % example_question_id,
            '      "value": "<answer value>",',
            '      "rationale": "Brief answer-specific reason.",',
            '      "confidence": 0.85',
            "    }",
            "  ]",
            "}",
            "```",
            "",
            "Use exact `questionId` values from the questionnaire.",
            "For choice questions, `value` must be the exact choice id (or list of ids for multi-select).",
        ]
    ).strip() + "\n"


def render_survey_instruction_markdown(instrument: SurveyInstrument) -> str:
    """Backward-compatible combined markdown from a normalized questionnaire."""
    content = SurveyTaskContent(
        title=instrument.title,
        instruction_markdown=render_survey_task_instruction_markdown(instrument),
        context_markdown=render_survey_context_markdown(instrument),
        questionnaire_markdown=render_survey_questionnaire_markdown(instrument),
        output_schema_markdown=render_survey_output_schema_markdown(instrument),
        instrument=instrument,
    )
    return content.combined_markdown().strip() + "\n"
