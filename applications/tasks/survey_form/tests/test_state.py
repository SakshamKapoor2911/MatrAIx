from __future__ import annotations

import json
import os
import sys
from pathlib import Path

OUTPUT_DIR = Path(os.environ.get("MATRIX_OUTPUT_DIR", "/app/output"))
RESULT_PATH = OUTPUT_DIR / "survey_result.json"
EVENT_KEYS = {"timestamp", "actor", "action", "context", "outcome"}


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def main() -> int:
    if not RESULT_PATH.is_file():
        return fail("missing {}".format(RESULT_PATH))
    try:
        payload = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail("survey_result.json is not valid JSON: {}".format(exc))
    if not isinstance(payload, dict):
        return fail("survey_result.json must contain an object")
    answers = payload.get("answers")
    if not isinstance(answers, list) or not answers:
        return fail("survey_result.answers must be a non-empty list")
    trajectory = payload.get("trajectory")
    if not isinstance(trajectory, list) or not trajectory:
        return fail("survey_result.trajectory must be a non-empty list")
    for index, answer in enumerate(answers):
        if not isinstance(answer, dict):
            return fail("answers[{}] must be an object".format(index))
        if not str(answer.get("questionId", "")).strip():
            return fail("answers[{}].questionId is required".format(index))
        if "value" not in answer:
            return fail("answers[{}].value is required".format(index))
    for index, event in enumerate(trajectory):
        if not isinstance(event, dict):
            return fail("trajectory[{}] must be an object".format(index))
        missing = EVENT_KEYS - set(event)
        if missing:
            return fail(
                "trajectory[{}] missing keys: {}".format(
                    index,
                    ", ".join(sorted(missing)),
                )
            )
        if not isinstance(event.get("context"), dict):
            return fail("trajectory[{}].context must be an object".format(index))
        if not isinstance(event.get("outcome"), dict):
            return fail("trajectory[{}].outcome must be an object".format(index))
    print("PASS: survey form output is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
