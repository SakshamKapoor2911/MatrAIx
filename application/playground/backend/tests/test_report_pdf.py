"""PDF report builders for Harbor batch and trial downloads."""

from __future__ import annotations

from backend.service.report_pdf import (
    build_batch_report_pdf,
    build_trial_report_pdf,
    pdf_filename,
)


def test_pdf_filename_sanitizes_parts():
    assert pdf_filename("job/a", "trial:b") == "job-a-trial-b.pdf"
    assert pdf_filename("demo-job", "batch-report") == "demo-job-batch-report.pdf"


def test_build_batch_report_pdf_returns_pdf_bytes():
    payload = build_batch_report_pdf(
        job_name="demo-job",
        job={
            "applicationType": "survey",
            "launch": {"status": "completed", "exitCode": 0, "configPath": "/tmp/cfg.yaml"},
            "result": {
                "started_at": "2026-07-12T00:00:00Z",
                "finished_at": "2026-07-12T00:01:00Z",
            },
            "trials": [
                {
                    "trialName": "trial-1",
                    "personaName": "Alex",
                    "completed": True,
                    "succeeded": True,
                }
            ],
        },
        aggregation={
            "generatedAt": "2026-07-12T00:00:00Z",
            "coverage": {
                "trialCount": 1,
                "completedTrials": 1,
                "pendingTrials": 0,
                "artifactReadyTrials": 1,
                "completedWithoutArtifactTrials": 0,
            },
            "reporting": {"status": "not_applicable", "model": "gpt-test"},
            "fields": [
                {
                    "key": "question.q1.response",
                    "label": "Selected response",
                    "kind": "categorical",
                    "presentCount": 1,
                    "missingCount": 0,
                    "categorical": {
                        "count": 1,
                        "distinctCount": 1,
                        "counts": [{"value": "incorrect_code_changes", "count": 1}],
                    },
                }
            ],
            "contexts": [
                {
                    "key": "question.q1",
                    "label": "What is your biggest concern?",
                    "contextType": "question_response",
                    "questionType": "single_choice",
                    "choiceOptions": [
                        {"id": "incorrect_code_changes", "label": "Incorrect code changes"},
                        {"id": "too_much_autonomy", "label": "Too much autonomy"},
                    ],
                    "facets": [
                        {
                            "key": "question.q1.response",
                            "label": "Selected response",
                            "kind": "categorical",
                            "role": "primary",
                            "presentCount": 1,
                            "missingCount": 0,
                            "categorical": {
                                "count": 1,
                                "distinctCount": 1,
                                "counts": [{"value": "incorrect_code_changes", "count": 1}],
                            },
                        }
                    ],
                }
            ],
        },
    )
    assert payload.startswith(b"%PDF")
    assert len(payload) > 500

    def _pdf_text(raw: bytes) -> str:
        import re
        import zlib

        chunks: list[str] = []
        for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S):
            data = match.group(1)
            try:
                data = zlib.decompress(data)
            except Exception:
                pass
            chunks.append(data.decode("latin-1", errors="ignore"))
        return "\n".join(chunks)

    text = _pdf_text(payload)
    assert "Per-question report" in text
    assert "Incorrect code changes" in text
    assert "What is your biggest concern?" in text
    # Flat field dump should not dominate when question contexts exist.
    assert text.count("Selected response") <= 2


def test_build_trial_report_pdf_survey_returns_pdf_bytes():
    payload = build_trial_report_pdf(
        job_name="demo-job",
        trial_name="trial-1",
        debrief={
            "applicationType": "survey",
            "createdAt": "2026-07-12T00:00:00Z",
            "persona": {"id": "p1", "name": "Alex", "source": "pool", "dimensions": {"age": "25-34"}},
            "config": {"taskPath": "application/tasks/example-survey_product-feedback"},
            "verifier": {"reward": 1.0, "passed": True, "details": "ok"},
            "surveyResult": {
                "completed": True,
                "instrument": {"id": "inst-1", "title": "Product feedback"},
                "answers": [
                    {
                        "questionId": "q1",
                        "value": 5,
                        "rationale": "Clear and useful.",
                    }
                ],
            },
        },
    )
    assert payload.startswith(b"%PDF")
    assert len(payload) > 400
