"""Render Harbor ``instruction.md`` from a built-in survey instrument."""

from __future__ import annotations

from backend.service.survey_types import SurveyInstrument, SurveyQuestion


def _render_question(question: SurveyQuestion) -> list[str]:
    lines = [f"### {question.id}", "", question.prompt, ""]
    if question.construct:
        lines.append(f"*Construct: {question.construct}*")
        lines.append("")
    if question.type == "likert":
        lines.append(
            "**Type:** Likert scale — set `value` to an integer **{}**–**{}**.".format(
                question.min_value,
                question.max_value,
            )
        )
    elif question.type == "single_choice":
        lines.append("**Type:** Single choice — set `value` to one **choice_id**:")
        for option in question.options:
            lines.append("- `{}`".format(option))
    elif question.type == "multi_choice":
        lines.append("**Type:** Multi choice — set `value` to a list of **choice_id** strings:")
        for option in question.options:
            lines.append("- `{}`".format(option))
    elif question.type == "free_text":
        lines.append("**Type:** Free text — set `value` to a short string in the persona's voice.")
    else:
        lines.append("**Type:** {}".format(question.type))
    lines.append("")
    return lines


def render_survey_instruction_markdown(instrument: SurveyInstrument) -> str:
    """Human-readable survey brief for Harbor tasks (product context + questions)."""
    lines = [
        "# {}".format(instrument.title),
        "",
        "You are the assigned persona. Read the context below and answer every question as that person would.",
        "",
        "Harbor runs this survey via **json_survey** (one-shot JSON completion). "
        "Your answers are saved to `/app/output/survey_result.json`.",
        "",
        "---",
        "",
        "## Context",
        "",
        instrument.description.strip()
        if instrument.description
        else "Answer each question as the assigned persona.",
        "",
        "---",
        "",
        "## Survey questions",
        "",
        "Use exact `questionId` values and valid `value` strings from the instrument JSON schema.",
        "Every answer needs a short **rationale** in the persona's voice and a **confidence** between 0 and 1.",
        "",
    ]
    for question in instrument.questions:
        lines.extend(_render_question(question))
    lines.extend(
        [
            "---",
            "",
            "## Output artifact",
            "",
            "Save to `/app/output/survey_result.json`:",
            "",
            "```json",
            "{",
            '  "instrument": {',
            '    "id": "{}",'.format(instrument.id),
            '    "title": "{}"'.format(instrument.title.replace('"', '\\"')),
            "  },",
            '  "answers": [',
            "    {",
            '      "questionId": "{}",'.format(instrument.questions[0].id if instrument.questions else "q1"),
            '      "value": "<answer>",',
            '      "rationale": "Brief persona-grounded reason.",',
            '      "confidence": 0.85',
            "    }",
            "  ],",
            '  "trajectory": []',
            "}",
            "```",
            "",
            "- Include one entry in `answers` for each question you answer.",
            "- The runtime fills `trajectory` automatically if you leave it empty.",
        ]
    )
    return "\n".join(lines).strip() + "\n"
