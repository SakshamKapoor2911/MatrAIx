"""Generate a demo batch PDF report for the 351 synthetic chatbot tasks.

Usage:
    uv run python application/scripts/generate_synthetic_chatbot_report_pdf.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from _repo_imports import ensure_application_script_imports

ensure_application_script_imports()

from backend.service.report_pdf import build_batch_report_pdf

REPO_ROOT = Path(__file__).resolve().parents[2]
TASKS_DIR = REPO_ROOT / "application" / "tasks"

DOMAIN_LABELS = {
    "arts": "Arts & Crafts",
    "automotive": "Automotive",
    "beauty": "Beauty & Personal Care",
    "education": "Education",
    "finance": "Finance & Banking",
    "fitness": "Fitness & Wellness",
    "healthcare": "Healthcare",
    "insurance": "Insurance",
    "legal": "Legal",
    "real-estate": "Real Estate",
    "retail": "Retail & E-commerce",
    "sustainability": "Sustainability",
    "technology": "Technology",
    "telecom": "Telecommunications",
    "travel": "Travel & Hospitality",
    "volunteering": "Volunteering & Nonprofit",
    "writing": "Writing & Publishing",
}

DOMAIN_INTENTS = {
    "education": ["Learn / explain", "Brainstorm", "Get task done"],
    "legal": ["Get task done", "Vent / support", "Decide"],
    "telecom": ["Vent / support", "Get task done"],
    "healthcare": ["Vent / support", "Get task done", "Learn / explain"],
    "travel": ["Get task done", "Decide"],
    "technology": ["Debug / troubleshoot", "Get task done", "Learn / explain"],
    "finance": ["Get task done", "Decide", "Learn / explain"],
    "insurance": ["Get task done", "Decide"],
    "real-estate": ["Get task done", "Decide"],
    "retail": ["Decide", "Get task done"],
    "arts": ["Learn / explain", "Brainstorm"],
    "automotive": ["Get task done", "Decide"],
    "beauty": ["Learn / explain", "Get task done"],
    "fitness": ["Learn / explain", "Get task done"],
    "sustainability": ["Learn / explain", "Get task done", "Brainstorm"],
    "volunteering": ["Get task done", "Learn / explain"],
    "writing": ["Brainstorm", "Learn / explain", "Get task done"],
}


def _collect_trials(tasks: list[dict]) -> list[dict]:
    trials = []
    for idx, task in enumerate(tasks, start=1):
        trials.append({
            "trialName": f"trial-{idx:03d}",
            "personaName": f"{task['name']}",
            "completed": True,
            "succeeded": True,
        })
    return trials


def _collect_contexts(tasks: list[dict]) -> list[dict]:
    outcome_statuses = ["resolved", "resolved", "resolved", "partially_resolved", "resolved"]
    resolution_bases = ["information_provided", "action_taken", "information_provided", "escalation_needed", "action_taken"]
    conv_paths = ["direct", "negotiation", "direct", "multi_step", "negotiation"]
    need_satisfactions = ["yes", "yes", "partially", "yes", "no"]
    clarifications = [True, True, False, True, True]

    domains_used = sorted({t["domain"] for t in tasks})
    task_outcome_facets = []
    conversation_summary_facets = []
    user_feedback_facets = []
    trial_summary_facets = []

    for domain in domains_used:
        intent_list = DOMAIN_INTENTS.get(domain, ["Get task done"])
        count = sum(1 for t in tasks if t["domain"] == domain)

        task_outcome_facets.append({
            "key": f"task_outcome.status_{domain}",
            "label": f"Outcome status · {DOMAIN_LABELS.get(domain, domain)}",
            "kind": "categorical",
            "role": "primary",
            "presentCount": count,
            "missingCount": 0,
            "categorical": {
                "count": count,
                "distinctCount": 2,
                "counts": [
                    {"value": "resolved", "count": count * 4 // 5},
                    {"value": "partially_resolved", "count": count - count * 4 // 5},
                ],
            },
        })
        task_outcome_facets.append({
            "key": f"task_outcome.resolution_{domain}",
            "label": f"Resolution basis · {DOMAIN_LABELS.get(domain, domain)}",
            "kind": "categorical",
            "presentCount": count,
            "missingCount": 0,
            "categorical": {
                "count": count,
                "distinctCount": 2,
                "counts": [
                    {"value": "information_provided", "count": count * 3 // 5},
                    {"value": "action_taken", "count": count - count * 3 // 5},
                ],
            },
        })

        conversation_summary_facets.append({
            "key": f"conv.path_{domain}",
            "label": f"Conversation path · {DOMAIN_LABELS.get(domain, domain)}",
            "kind": "categorical",
            "presentCount": count,
            "missingCount": 0,
            "categorical": {
                "count": count,
                "distinctCount": 3,
                "counts": [
                    {"value": "direct", "count": count * 2 // 5},
                    {"value": "negotiation", "count": count * 2 // 5},
                    {"value": "multi_step", "count": count - count * 4 // 5},
                ],
            },
        })

        user_feedback_facets.append({
            "key": f"feedback.need_sat_{domain}",
            "label": f"Need satisfaction · {DOMAIN_LABELS.get(domain, domain)}",
            "kind": "categorical",
            "presentCount": count,
            "missingCount": 0,
            "categorical": {
                "count": count,
                "distinctCount": 3,
                "counts": [
                    {"value": "yes", "count": count * 3 // 5},
                    {"value": "partially", "count": count // 5},
                    {"value": "no", "count": count - count * 4 // 5},
                ],
            },
        })
        user_feedback_facets.append({
            "key": f"feedback.rating_{domain}",
            "label": f"Experience rating (1-10) · {DOMAIN_LABELS.get(domain, domain)}",
            "kind": "numerical",
            "presentCount": count,
            "missingCount": 0,
            "numerical": {"avg": 7.2, "min": 3.0, "max": 10.0, "std": 1.5, "p25": 6.0, "p50": 8.0, "p75": 9.0},
        })

    trial_summary_facets = [
        {"key": "trial_count", "label": "Total trials", "kind": "numerical", "numerical": {"avg": len(tasks)}},
        {"key": "pass_rate", "label": "Pass rate", "kind": "numerical", "numerical": {"avg": 0.95, "min": 0.80, "max": 1.0}},
        {"key": "turns_per_trial", "label": "Turns per trial", "kind": "numerical", "numerical": {"avg": 4.2, "min": 2.0, "max": 8.0}},
    ]

    return [
        {
            "key": "task_outcome",
            "label": "Task outcome",
            "contextType": "task_outcome",
            "facets": task_outcome_facets,
        },
        {
            "key": "conversation_summary",
            "label": "Conversation summary",
            "contextType": "conversation_summary",
            "facets": conversation_summary_facets,
        },
        {
            "key": "user_feedback",
            "label": "User feedback",
            "contextType": "user_feedback",
            "facets": user_feedback_facets,
        },
        {
            "key": "trial_summary",
            "label": "Trial summary",
            "contextType": "trial_summary",
            "facets": trial_summary_facets,
        },
    ]


def _collect_fields(tasks: list[dict]) -> list[dict]:
    return [
        {
            "key": "domain_coverage",
            "label": "Domains covered",
            "kind": "categorical",
            "presentCount": len(tasks),
            "missingCount": 0,
            "categorical": {
                "count": len(tasks),
                "distinctCount": len(set(t["domain"] for t in tasks)),
                "counts": [],
            },
        },
        {
            "key": "contract_tests",
            "label": "Contract tests passing",
            "kind": "categorical",
            "presentCount": 1,
            "missingCount": 0,
            "categorical": {
                "count": 1,
                "distinctCount": 1,
                "counts": [{"value": "381 passed", "count": 1}],
            },
        },
    ]


def main():
    task_dirs = sorted([
        d for d in TASKS_DIR.iterdir()
        if d.is_dir() and d.name.endswith("_chatbot") and not d.name.startswith(("example-", "chat_", "meal-", "rasa-", "recommender-"))
    ])

    tasks = []
    for d in task_dirs:
        name = d.name
        domain = name.split("-")[0] if "-" in name else "general"
        tasks.append({"name": name, "domain": domain, "path": str(d.relative_to(TASKS_DIR))})

    domains = sorted(set(t["domain"] for t in tasks))
    print(f"Found {len(tasks)} synthetic chatbot tasks across {len(domains)} domains")
    print(f"Domains: {', '.join(domains)}")

    trials = _collect_trials(tasks)
    contexts = _collect_contexts(tasks)
    fields = _collect_fields(tasks)

    job = {
        "applicationType": "chatbot",
        "launch": {
            "status": "completed",
            "exitCode": 0,
            "configPath": "configs/jobs/application-task-job-recipe/synthetic-chatbot-demo-n8.yaml",
        },
        "result": {
            "started_at": "2026-07-17T00:00:00Z",
            "finished_at": "2026-07-17T00:15:00Z",
        },
        "trials": trials,
    }

    aggregation = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "coverage": {
            "trialCount": len(trials),
            "completedTrials": len(trials),
            "pendingTrials": 0,
            "artifactReadyTrials": len(trials),
            "completedWithoutArtifactTrials": 0,
        },
        "reporting": {
            "status": "completed",
            "model": "verifier_test",
            "aggregationMode": "local_demo",
        },
        "fields": fields,
        "contexts": contexts,
    }

    pdf_bytes = build_batch_report_pdf(
        job_name="synthetic-chatbot-351-full-batch",
        job=job,
        aggregation=aggregation,
    )

    output_path = REPO_ROOT / "application" / "synthetic-chatbot-351-demo-batch-report.pdf"
    output_path.write_bytes(pdf_bytes)
    print(f"\nPDF generated: {output_path} ({len(pdf_bytes)} bytes)")


if __name__ == "__main__":
    main()
