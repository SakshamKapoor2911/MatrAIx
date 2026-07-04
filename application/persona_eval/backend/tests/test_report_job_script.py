from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_DIR = REPO_ROOT / "application" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from report_job import run_job_reporting  # noqa: E402


class _FakeChatClient:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls = 0

    def complete_json(self, system: str, user: str) -> dict:
        del system, user
        self.calls += 1
        return self.response


def test_run_job_reporting_executes_llm_and_clears_status_file(tmp_path: Path) -> None:
    repo_root = tmp_path
    job_dir = repo_root / "jobs" / "demo-job"
    trial_dir = job_dir / "trial-1"
    (trial_dir / "verifier").mkdir(parents=True, exist_ok=True)
    (trial_dir / "result.json").write_text("{}", encoding="utf-8")
    (trial_dir / "verifier" / "structured_output.json").write_text(
        json.dumps(
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
                        "facets": [
                            {"key": "response", "label": "Response", "role": "primary", "kind": "categorical", "value": "yes"},
                            {"key": "reason", "label": "Reason", "role": "explanation", "kind": "textual", "value": "Affordable and simple."},
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    client = _FakeChatClient(
        {
            "overallSummary": "Affordability is the main theme.",
            "bucketSummaries": [
                {
                    "bucket": "yes",
                    "summary": "Positive responses cite affordability and simplicity.",
                }
            ],
        }
    )

    aggregation = run_job_reporting(
        job_dir,
        repo_root=repo_root,
        enable_llm=True,
        llm_client=client,
    )

    assert aggregation["reporting"]["status"] == "completed"
    assert aggregation["contexts"][0]["summaries"][0]["status"] == "llm_completed"
    assert client.calls == 1
    assert not (job_dir / "reporting_status.json").exists()
