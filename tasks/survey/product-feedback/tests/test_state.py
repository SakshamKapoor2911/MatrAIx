import json
from pathlib import Path

OUTPUT = Path("/app/output/survey_responses.json")
REQUIRED_QUESTION_IDS = {"q1", "q2", "q3", "q4", "q5"}


def _load() -> dict:
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"
    data = json.loads(OUTPUT.read_text())
    assert isinstance(data, dict), "root must be an object"
    return data


def test_output_exists():
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"


def test_output_schema():
    data = _load()
    responses = data.get("responses")
    assert isinstance(responses, list) and responses, "responses must be a non-empty list"

    seen_ids: set[str] = set()
    for entry in responses:
        assert isinstance(entry, dict), "each response must be an object"
        qid = entry.get("question_id")
        answer = entry.get("answer")
        assert isinstance(qid, str) and qid.strip(), "question_id must be a non-empty string"
        assert isinstance(answer, str) and answer.strip(), "answer must be a non-empty string"
        seen_ids.add(qid.strip())

    assert REQUIRED_QUESTION_IDS <= seen_ids, (
        f"missing question_ids: {sorted(REQUIRED_QUESTION_IDS - seen_ids)}"
    )

    interest = data.get("overall_interest")
    assert isinstance(interest, int) and 1 <= interest <= 5, (
        "overall_interest must be an integer from 1 to 5"
    )

    assert isinstance(data.get("would_try_beta"), bool), "would_try_beta must be boolean"

    summary = data.get("summary")
    assert isinstance(summary, str) and len(summary.strip()) >= 20, "summary is too short"
