"""Integration test: full pipeline - sidecar conversation + verifier."""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from server import create_session, post_message, get_conversation


def main() -> int:
    tmpdir = tempfile.mkdtemp()
    os.environ["PERSONABENCH_OUTPUT_DIR"] = tmpdir
    os.environ["PERSONABENCH_VERIFIER_DIR"] = tmpdir
    output_dir = Path(tmpdir)

    resp = create_session()
    sid = resp["sessionId"]
    post_message(sid, "Hi, I need a meal plan.")
    post_message(sid, "I am vegetarian, trying to eat healthier.")
    post_message(sid, "I want to lose weight, lightly active, female, 30.")
    post_message(sid, "Can I substitute quinoa for brown rice?")

    conv = get_conversation(sid)
    transcript_path = output_dir / "transcript.json"
    transcript_path.write_text(json.dumps(conv, indent=2), encoding="utf-8")

    feedback = {
        "needConstraintSatisfaction": "yes",
        "personalPreferenceSatisfaction": "partially",
        "overallExperienceRating": 7,
        "reason": "Good plan, but I wish there were more variety in vegetables.",
        "askedUsefulClarificationQuestions": True,
        "clarifyingNotes": "Questions about diet and activity were useful.",
        "trustLevel": 7,
        "feltUnderstood": True,
        "safetyFlagged": True,
        "adherenceLikelihood": 7,
    }
    feedback_path = output_dir / "user_feedback.json"
    feedback_path.write_text(json.dumps(feedback, indent=2), encoding="utf-8")

    tests_dir = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
    tests_dir = tests_dir / "application" / "tasks" / "meal-planning-nutrition_chatbot" / "tests"
    test_state_py = tests_dir / "test_state.py"
    sys.path.insert(0, str(tests_dir))

    spec = importlib.util.spec_from_file_location("test_state", str(test_state_py))
    test_state = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(test_state)
    verify = test_state.main

    try:
        verify()
        print("PASS: Verifier ran successfully")
        structured_path = Path(tmpdir) / "structured_output.json"
        if structured_path.exists():
            data = json.loads(structured_path.read_text(encoding="utf-8"))
            contexts = {c["contextType"]: c for c in data["contexts"]}
            assert "task_outcome" in contexts
            assert "conversation_summary" in contexts
            assert "user_feedback" in contexts
            fo = contexts["task_outcome"]["facets"][0]
            print(f"  Outcome status: {fo['value']}")
            fc = contexts["conversation_summary"]["facets"][2]
            print(f"  Messages: {fc['value']}")
        return 0
    except (AssertionError, SystemExit) as exc:
        code = exc.code if isinstance(exc, SystemExit) else 1
        print(f"FAIL: Verifier failed: {exc}")
        return code


if __name__ == "__main__":
    sys.exit(main())
