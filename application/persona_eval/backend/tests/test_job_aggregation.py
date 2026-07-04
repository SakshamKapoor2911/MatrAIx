from __future__ import annotations

import json
from pathlib import Path

from backend.service.job_aggregation import build_job_aggregation


def _write_trial(job_dir: Path, trial_name: str, payload: dict) -> None:
    trial_dir = job_dir / trial_name
    (trial_dir / "verifier").mkdir(parents=True, exist_ok=True)
    (trial_dir / "result.json").write_text("{}", encoding="utf-8")
    (trial_dir / "verifier" / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class _FakeChatClient:
    def __init__(self, responses: list[dict]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def complete_json(self, system: str, user: str) -> dict:
        self.calls.append((system, user))
        assert self._responses, "unexpected extra LLM call"
        return self._responses.pop(0)


def test_build_job_aggregation_groups_text_by_categorical_directive(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    payload_yes = {
        "presenceCheck": {"passed": True},
        "contexts": [
            {
                "key": "question.q1",
                "label": "Question 1",
                "contextType": "question_response",
                "summaryDirectives": [
                    {
                        "id": "q1.reason_by_response",
                        "title": "Reason by response",
                        "targetFacetKey": "reason",
                        "groupByFacetKey": "response",
                        "groupByMode": "categorical",
                        "summaryKind": "llm_bucket_summary",
                    }
                ],
                "facets": [
                    {"key": "response", "label": "Response", "role": "primary", "kind": "categorical", "value": "yes"},
                    {"key": "reason", "label": "Reason", "role": "explanation", "kind": "textual", "value": "Easy to use."},
                ],
            }
        ],
    }
    payload_no = {
        "presenceCheck": {"passed": True},
        "contexts": [
            {
                "key": "question.q1",
                "label": "Question 1",
                "contextType": "question_response",
                "summaryDirectives": [
                    {
                        "id": "q1.reason_by_response",
                        "title": "Reason by response",
                        "targetFacetKey": "reason",
                        "groupByFacetKey": "response",
                        "groupByMode": "categorical",
                        "summaryKind": "llm_bucket_summary",
                    }
                ],
                "facets": [
                    {"key": "response", "label": "Response", "role": "primary", "kind": "categorical", "value": "no"},
                    {"key": "reason", "label": "Reason", "role": "explanation", "kind": "textual", "value": "Too expensive."},
                ],
            }
        ],
    }
    _write_trial(job_dir, "trial-1", payload_yes)
    _write_trial(job_dir, "trial-2", payload_no)

    aggregation = build_job_aggregation(job_dir)

    assert aggregation is not None
    contexts = aggregation["contexts"]
    assert len(contexts) == 1
    summaries = contexts[0]["summaries"]
    assert summaries[0]["id"] == "q1.reason_by_response"
    buckets = {bucket["bucket"]: bucket for bucket in summaries[0]["buckets"]}
    assert buckets["yes"]["count"] == 1
    assert buckets["no"]["count"] == 1
    assert buckets["yes"]["summary"]


def test_build_job_aggregation_groups_text_by_numeric_band_directive(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    for name, score, text in [
        ("trial-low", 2, "Low confidence reason."),
        ("trial-high", 9, "High confidence reason."),
    ]:
        _write_trial(
            job_dir,
            name,
            {
                "presenceCheck": {"passed": True},
                "contexts": [
                    {
                        "key": "decision.review",
                        "label": "Decision review",
                        "contextType": "decision",
                        "summaryDirectives": [
                            {
                                "id": "decision.reason_by_confidence",
                                "title": "Reason by confidence",
                                "targetFacetKey": "reason",
                                "groupByFacetKey": "confidence",
                                "groupByMode": "numeric_band",
                                "bands": [
                                    {"label": "low", "min": 0, "max": 3},
                                    {"label": "high", "min": 8, "max": 10},
                                ],
                                "summaryKind": "llm_bucket_summary",
                            }
                        ],
                        "facets": [
                            {"key": "confidence", "label": "Confidence", "role": "score", "kind": "numerical", "value": score},
                            {"key": "reason", "label": "Reason", "role": "explanation", "kind": "textual", "value": text},
                        ],
                    }
                ],
            },
        )

    aggregation = build_job_aggregation(job_dir)

    assert aggregation is not None
    summaries = aggregation["contexts"][0]["summaries"]
    buckets = {bucket["bucket"]: bucket for bucket in summaries[0]["buckets"]}
    assert buckets["low"]["count"] == 1
    assert buckets["high"]["count"] == 1


def test_build_job_aggregation_reads_task_reporting_config(tmp_path: Path) -> None:
    repo_root = tmp_path
    task_dir = repo_root / "application" / "tasks" / "example-task"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "reporting.json").write_text(
        json.dumps(
            {
                "contextRules": [
                    {
                        "match": {"key": "decision.review"},
                        "summaryDirectives": [
                            {
                                "id": "decision.reason_by_choice",
                                "title": "Reason by choice",
                                "targetFacetKey": "reason",
                                "groupByFacetKey": "choice",
                                "groupByMode": "categorical",
                                "summaryKind": "llm_bucket_summary",
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    job_dir = repo_root / "jobs" / "job"
    trial_dir = job_dir / "trial-1"
    (trial_dir / "verifier").mkdir(parents=True, exist_ok=True)
    (trial_dir / "result.json").write_text("{}", encoding="utf-8")
    (trial_dir / "config.json").write_text(
        json.dumps({"task": {"path": "application/tasks/example-task"}}),
        encoding="utf-8",
    )
    (trial_dir / "verifier" / "structured_output.json").write_text(
        json.dumps(
            {
                "presenceCheck": {"passed": True},
                "contexts": [
                    {
                        "key": "decision.review",
                        "label": "Decision review",
                        "contextType": "decision",
                        "facets": [
                            {
                                "key": "choice",
                                "label": "Choice",
                                "role": "primary",
                                "kind": "categorical",
                                "value": "yes",
                            },
                            {
                                "key": "reason",
                                "label": "Reason",
                                "role": "explanation",
                                "kind": "textual",
                                "value": "It was straightforward.",
                            },
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    aggregation = build_job_aggregation(job_dir, repo_root=repo_root)

    assert aggregation is not None
    summaries = aggregation["contexts"][0]["summaries"]
    assert summaries[0]["id"] == "decision.reason_by_choice"
    assert summaries[0]["buckets"][0]["bucket"] == "yes"


def test_build_job_aggregation_synthesizes_user_feedback_context(tmp_path: Path) -> None:
    repo_root = tmp_path
    task_dir = repo_root / "application" / "tasks" / "example-web-playwright_quote-choice"
    input_dir = task_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "reporting.json").write_text(
        json.dumps(
            {
                "contextRules": [
                    {
                        "match": {"contextType": "user_feedback"},
                        "summaryDirectives": [
                            {
                                "id": "user_feedback.reason_by_need_satisfaction",
                                "title": "Feedback reason by need satisfaction",
                                "targetFacetKey": "feedback_reason",
                                "groupByFacetKey": "need_constraint_satisfaction",
                                "groupByMode": "categorical",
                                "summaryKind": "llm_bucket_summary",
                            }
                        ],
                        "judgeDirectives": [
                            {
                                "id": "user_feedback.reason_signal_scan",
                                "title": "Feedback signal scan",
                                "targetFacetKey": "feedback_reason",
                                "groupByFacetKey": "personal_preference_satisfaction",
                                "groupByMode": "categorical",
                                "judgeKind": "llm_signal_judge",
                                "prompt": "Read the persona's feedback and classify signals.",
                                "rubric": "Only mark present when explicit.",
                                "signals": [
                                    {
                                        "key": "trust_signal",
                                        "label": "Trust or confidence",
                                        "valueType": "boolean",
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (input_dir / "self_report_schema.yaml").write_text(
        "\n".join(
            [
                "artifactName: user_feedback.json",
                "fields:",
                "  - key: needConstraintSatisfaction",
                "    prompt: How well did the choice satisfy your need?",
                "    kind: enum",
                "  - key: personalPreferenceSatisfaction",
                "    prompt: How well did it match your preferences?",
                "    kind: enum",
                "  - key: overallExperienceRating",
                "    prompt: Overall rating",
                "    kind: integer",
                "  - key: reason",
                "    prompt: Why?",
                "  - key: trustLevel",
                "    prompt: Trust level",
                "    kind: integer",
                "  - key: clarityOfNextStep",
                "    prompt: Was the next step clear?",
                "    kind: boolean",
                "",
            ]
        ),
        encoding="utf-8",
    )
    job_dir = repo_root / "jobs" / "job"
    trial_dir = job_dir / "trial-1"
    output_dir = trial_dir / "artifacts" / "app" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (trial_dir / "verifier").mkdir(parents=True, exist_ok=True)
    (trial_dir / "result.json").write_text("{}", encoding="utf-8")
    (trial_dir / "config.json").write_text(
        json.dumps({"task": {"path": "application/tasks/example-web-playwright_quote-choice"}}),
        encoding="utf-8",
    )
    (output_dir / "user_feedback.json").write_text(
        json.dumps(
            {
                "needConstraintSatisfaction": "yes",
                "personalPreferenceSatisfaction": "partially",
                "overallExperienceRating": 8,
                "reason": "The site felt trustworthy and I knew what to do next.",
                "trustLevel": 9,
                "clarityOfNextStep": True,
            }
        ),
        encoding="utf-8",
    )
    (trial_dir / "verifier" / "structured_output.json").write_text(
        json.dumps(
            {
                "presenceCheck": {"passed": True},
                "contexts": [
                    {
                        "key": "decision.primary",
                        "label": "Primary decision",
                        "contextType": "decision",
                        "facets": [
                            {
                                "key": "decision_outcome",
                                "label": "Decision outcome",
                                "role": "primary",
                                "kind": "categorical",
                                "value": "selected",
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    aggregation = build_job_aggregation(job_dir, repo_root=repo_root)

    assert aggregation is not None
    feedback_context = next(
        context
        for context in aggregation["contexts"]
        if context["contextType"] == "user_feedback"
    )
    facets = {facet["facetKey"]: facet for facet in feedback_context["facets"]}
    assert facets["feedback_reason"]["textual"]["count"] == 1
    assert facets["need_constraint_satisfaction"]["categorical"]["counts"][0]["value"] == "yes"
    assert facets["trust_level"]["numerical"]["avg"] == 9.0
    assert facets["clarity_of_next_step"]["categorical"]["counts"][0]["value"] == "true"
    assert feedback_context["summaries"][0]["id"] == "user_feedback.reason_by_need_satisfaction"
    assert feedback_context["judges"][0]["id"] == "user_feedback.reason_signal_scan"
    assert aggregation["reporting"]["status"] == "ready"
    assert aggregation["reporting"]["totalUnits"] == 2


def test_build_job_aggregation_emits_judge_units(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    _write_trial(
        job_dir,
        "trial-1",
        {
            "presenceCheck": {"passed": True},
            "contexts": [
                {
                    "key": "question.q1",
                    "label": "Question 1",
                    "contextType": "question_response",
                    "facets": [
                        {"key": "response", "label": "Response", "role": "primary", "kind": "categorical", "value": "yes"},
                        {"key": "reason", "label": "Reason", "role": "explanation", "kind": "textual", "value": "It is affordable."},
                    ],
                    "judgeDirectives": [
                        {
                            "id": "question.reason_signal_scan",
                            "title": "Reason signal scan",
                            "targetFacetKey": "reason",
                            "groupByFacetKey": "response",
                            "groupByMode": "categorical",
                            "judgeKind": "llm_signal_judge",
                            "prompt": "Read the reason and classify signals.",
                            "rubric": "Set true only when the signal is explicit.",
                            "signals": [
                                {
                                    "key": "price_sensitivity",
                                    "label": "Price sensitivity",
                                    "valueType": "boolean",
                                }
                            ],
                        }
                    ],
                }
            ],
        },
    )

    aggregation = build_job_aggregation(job_dir)

    assert aggregation is not None
    judges = aggregation["contexts"][0]["judges"]
    assert judges[0]["id"] == "question.reason_signal_scan"
    assert judges[0]["signals"][0]["key"] == "price_sensitivity"
    assert judges[0]["rubric"] == "Set true only when the signal is explicit."
    assert judges[0]["status"] == "ready_for_llm"
    assert judges[0]["buckets"][0]["bucket"] == "yes"
    assert aggregation["reporting"]["status"] == "ready"
    assert aggregation["reporting"]["totalUnits"] == 1


def test_build_job_aggregation_executes_and_caches_llm_reporting(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    _write_trial(
        job_dir,
        "trial-1",
        {
            "presenceCheck": {"passed": True},
            "contexts": [
                {
                    "key": "question.q1",
                    "label": "Question 1",
                    "contextType": "question_response",
                    "summaryDirectives": [
                        {
                            "id": "question.reason_summary",
                            "title": "Reason summary",
                            "targetFacetKey": "reason",
                            "groupByFacetKey": "response",
                            "groupByMode": "categorical",
                            "summaryKind": "llm_bucket_summary",
                        }
                    ],
                    "judgeDirectives": [
                        {
                            "id": "question.reason_judge",
                            "title": "Reason judge",
                            "targetFacetKey": "reason",
                            "groupByFacetKey": "response",
                            "groupByMode": "categorical",
                            "judgeKind": "llm_signal_judge",
                            "prompt": "Spot pricing signals.",
                            "rubric": "Only mark present when explicit.",
                            "signals": [
                                {
                                    "key": "price_sensitivity",
                                    "label": "Price sensitivity",
                                    "valueType": "boolean",
                                }
                            ],
                        }
                    ],
                    "facets": [
                        {"key": "response", "label": "Response", "role": "primary", "kind": "categorical", "value": "yes"},
                        {"key": "reason", "label": "Reason", "role": "explanation", "kind": "textual", "value": "It is affordable and easy to use."},
                    ],
                }
            ],
        },
    )
    client = _FakeChatClient(
        [
            {
                "overallSummary": "Participants liked the affordability rationale.",
                "bucketSummaries": [
                    {
                        "bucket": "yes",
                        "summary": "Affordable pricing was the main reason for positive responses.",
                    }
                ],
            },
            {
                "overallAssessment": "Pricing language is explicit in the positive bucket.",
                "bucketAssessments": [
                    {
                        "bucket": "yes",
                        "assessment": "This bucket repeatedly mentions affordability.",
                        "signals": [
                            {
                                "key": "price_sensitivity",
                                "present": True,
                                "evidence": "affordable",
                            }
                        ],
                    }
                ],
            },
        ]
    )

    aggregation = build_job_aggregation(job_dir, llm_client=client, enable_llm=True)

    assert aggregation is not None
    summary = aggregation["contexts"][0]["summaries"][0]
    judge = aggregation["contexts"][0]["judges"][0]
    assert summary["status"] == "llm_completed"
    assert summary["overall"]["summary"] == "Participants liked the affordability rationale."
    assert summary["buckets"][0]["summaryType"] == "llm"
    assert judge["status"] == "llm_completed"
    assert judge["overallAssessment"] == "Pricing language is explicit in the positive bucket."
    assert judge["buckets"][0]["assessment"] == "This bucket repeatedly mentions affordability."
    assert judge["buckets"][0]["signals"][0]["key"] == "price_sensitivity"
    assert judge["buckets"][0]["signals"][0]["present"] is True
    assert aggregation["reporting"]["status"] == "completed"
    assert aggregation["reporting"]["completedUnits"] == 2
    assert len(client.calls) == 2

    cached_only = build_job_aggregation(job_dir, enable_llm=False)

    assert cached_only is not None
    cached_summary = cached_only["contexts"][0]["summaries"][0]
    cached_judge = cached_only["contexts"][0]["judges"][0]
    assert cached_summary["status"] == "llm_completed"
    assert cached_summary["buckets"][0]["summary"] == "Affordable pricing was the main reason for positive responses."
    assert cached_judge["status"] == "llm_completed"
    assert cached_judge["buckets"][0]["assessment"] == "This bucket repeatedly mentions affordability."
    assert cached_only["reporting"]["status"] == "completed"
