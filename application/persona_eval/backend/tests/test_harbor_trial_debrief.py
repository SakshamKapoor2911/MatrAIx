"""Tests for Harbor trial → PersonaEval debrief mapping."""

from __future__ import annotations

import json
from pathlib import Path

from backend.service.harbor_trial_debrief import map_trial_debrief


def _write_chat_trial(repo: Path, job_name: str, trial_name: str) -> None:
    persona_path = repo / "persona" / "datasets" / "bench-dev-sample" / "persona_0042.yaml"
    persona_path.parent.mkdir(parents=True, exist_ok=True)
    persona_path.write_text(
        "persona_id: '0042'\nversion: '1.0'\nsource: Nemotron\ndimensions: {}\n",
        encoding="utf-8",
    )
    trial_dir = repo / "jobs" / job_name / trial_name
    output = trial_dir / "artifacts" / "app" / "output"
    output.mkdir(parents=True)
    (output / "transcript.json").write_text(
        json.dumps(
            {
                "domain": "movie",
                "turns": [
                    {
                        "userMessage": "Hi",
                        "assistantMessage": "Hello",
                        "recommendedItems": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (output / "recommendation_result.json").write_text(
        json.dumps({"recommendedItems": [], "turnsToRecommendation": 1}),
        encoding="utf-8",
    )
    (output / "user_feedback.json").write_text(
        json.dumps({"overallExperienceRating": 7, "reason": "Okay."}),
        encoding="utf-8",
    )
    (trial_dir / "result.json").write_text(
        json.dumps(
            {
                "config": {
                    "agent": {
                        "kwargs": {
                            "persona_path": "persona/datasets/bench-dev-sample/persona_0042.yaml",
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )


def test_map_trial_debrief_chatbot(tmp_path: Path) -> None:
    repo = tmp_path
    _write_chat_trial(repo, "job-1", "trial-0")
    debrief = map_trial_debrief(
        repo_root=repo,
        jobs_dir=repo / "jobs",
        job_name="job-1",
        trial_name="trial-0",
    )
    assert debrief["applicationType"] == "chatbot"
    assert debrief["transcript"][0]["assistantMessage"] == "Hello"
    assert debrief["harbor"]["trialName"] == "trial-0"


def test_map_trial_debrief_includes_verifier(tmp_path: Path) -> None:
    repo = tmp_path
    _write_chat_trial(repo, "job-v", "trial-v")
    trial_dir = repo / "jobs" / "job-v" / "trial-v"
    (trial_dir / "reward.txt").write_text("1.0\n", encoding="utf-8")
    verifier_dir = trial_dir / "verifier"
    verifier_dir.mkdir()
    (verifier_dir / "test-stdout.txt").write_text("all checks passed\n", encoding="utf-8")
    debrief = map_trial_debrief(
        repo_root=repo,
        jobs_dir=repo / "jobs",
        job_name="job-v",
        trial_name="trial-v",
    )
    assert debrief["verifier"]["passed"] is True
    assert debrief["verifier"]["reward"] == 1.0
    assert "checks passed" in debrief["verifier"]["detail"]


def test_map_trial_debrief_survey_responses(tmp_path: Path) -> None:
    repo = tmp_path
    trial_dir = repo / "jobs" / "job-2" / "trial-a"
    output = trial_dir / "artifacts" / "app" / "output"
    output.mkdir(parents=True)
    (output / "survey_responses.json").write_text(
        json.dumps(
            {
                "responses": [
                    {"question_id": "q0", "choice_id": "q0_pay_when_roi_clear"},
                ]
            }
        ),
        encoding="utf-8",
    )
    debrief = map_trial_debrief(
        repo_root=repo,
        jobs_dir=repo / "jobs",
        job_name="job-2",
        trial_name="trial-a",
    )
    assert debrief["applicationType"] == "survey"
    assert debrief["surveyResult"]["answers"][0]["questionId"] == "q0"
