#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python3 <<'PY'
import json
from pathlib import Path

output = Path("/app/output/survey_responses.json")

payload = {
    "responses": [
        {
            "question_id": "q1",
            "answer": (
                "A single shared weekly view would reduce the mental load of "
                "tracking school and family errands across WeChat and email."
            ),
        },
        {
            "question_id": "q2",
            "answer": (
                "I worry about setup friction and whether another app duplicates "
                "calendars we already use without enough payoff."
            ),
        },
        {
            "question_id": "q3",
            "answer": (
                "Plus pricing seems reasonable if digest and handoffs work reliably; "
                "Pro only makes sense if email parsing is accurate."
            ),
        },
        {
            "question_id": "q4",
            "answer": (
                "Sunday evening could work for planning the week ahead, though "
                "timing might shift if we travel."
            ),
        },
        {
            "question_id": "q5",
            "answer": (
                "Comfortable only with explicit review before events are added; "
                "I would not trust fully automatic imports."
            ),
        },
    ],
    "overall_interest": 4,
    "would_try_beta": True,
    "summary": (
        "The concept addresses a real coordination problem for our household. "
        "I would try a beta if onboarding is quick and school parsing stays opt-in."
    ),
}

output.write_text(json.dumps(payload, indent=2) + "\n")
PY
