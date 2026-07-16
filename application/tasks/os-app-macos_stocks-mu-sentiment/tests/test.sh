#!/usr/bin/env bash
set -uo pipefail

# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/verifier_env.sh"

# Ensure VERIFIER_DIR exists and is writable; fall back to /tmp if not.
if ! mkdir -p "${VERIFIER_DIR}" 2>/dev/null || ! [ -w "${VERIFIER_DIR}" ]; then
  VERIFIER_DIR="/tmp/verifier_output"
  mkdir -p "${VERIFIER_DIR}"
fi
export VERIFIER_DIR

set +e
python3 <<'PY'
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

path = Path("/tmp/os-app-macos-stocks-mu-sentiment/sentiment.json")

if not path.is_file():
    logs_root = Path("/tmp/harbor/logs") if Path("/tmp/harbor/logs").is_dir() else Path("/logs")
    fa_path = logs_root / "agent" / "final_answer.txt"
    if fa_path.is_file():
        raw = fa_path.read_text(encoding="utf-8", errors="replace").strip()
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            try:
                candidate = json.loads(match.group())
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(candidate, indent=2, ensure_ascii=False))
            except (json.JSONDecodeError, OSError):
                pass

if not path.is_file():
    sys.exit(f"missing {path}")

data = json.loads(path.read_text())

# --- Validate ticker ---
if data.get("ticker") != "MU":
    sys.exit("ticker must be 'MU'")

# --- viewed_chart ---
if data.get("viewed_chart") is not True:
    sys.exit("viewed_chart must be true")

# --- timeframes_checked ---
timeframes = data.get("timeframes_checked")
if not isinstance(timeframes, list):
    sys.exit("timeframes_checked must be a list")
tf_set = set(timeframes)
if "1W" not in tf_set:
    sys.exit("timeframes_checked must include '1W'")
if "1M" not in tf_set:
    sys.exit("timeframes_checked must include '1M'")
if "1Y" not in tf_set:
    sys.exit("timeframes_checked must include '1Y'")
if not tf_set.intersection({"3M", "2Y"}):
    sys.exit("timeframes_checked must include at least one of '3M' or '2Y'")

# --- trend_summary ---
trend_summary = data.get("trend_summary")
if not isinstance(trend_summary, dict):
    sys.exit("trend_summary must be an object")
for tf in timeframes:
    desc = trend_summary.get(tf, "")
    if not isinstance(desc, str) or len(desc.strip()) < 10:
        sys.exit(f"trend_summary['{tf}'] must be at least 10 characters")

# --- news_articles_read ---
news = data.get("news_articles_read")
if not isinstance(news, list):
    sys.exit("news_articles_read must be a list")
for i, article in enumerate(news):
    if not isinstance(article, dict):
        sys.exit(f"news_articles_read[{i}] must be an object")
    headline = article.get("headline", "")
    if not isinstance(headline, str) or not headline.strip():
        sys.exit(f"news_articles_read[{i}].headline must be non-empty")
    summary = article.get("summary", "")
    if not isinstance(summary, str) or len(summary.strip()) < 20:
        sys.exit(f"news_articles_read[{i}].summary must be at least 20 characters")
    relevance = article.get("relevance", "")
    if not isinstance(relevance, str) or len(relevance.strip()) < 10:
        sys.exit(f"news_articles_read[{i}].relevance must be at least 10 characters")

# --- sentiment ---
sentiment = data.get("sentiment")
valid_sentiments = {"buy", "sell", "hold"}
if sentiment not in valid_sentiments:
    sys.exit(f"sentiment must be one of: {valid_sentiments}")

# --- confidence ---
confidence = data.get("confidence")
if not isinstance(confidence, (int, float)):
    sys.exit("confidence must be numeric")
confidence = int(round(float(confidence)))
if not 1 <= confidence <= 10:
    sys.exit("confidence must be between 1 and 10")

# --- reasoning ---
reasoning = data.get("reasoning", "")
if not isinstance(reasoning, str) or len(reasoning.strip()) < 50:
    sys.exit("reasoning must be at least 50 characters")

# --- Load optional user feedback ---
feedback_path = Path("/app/output/user_feedback.json")
satisfaction_buckets = {"yes", "partially", "no"}
influence_buckets = {"heavily", "somewhat", "minimally"}


def load_user_feedback() -> dict[str, object] | None:
    if not feedback_path.is_file():
        return None
    feedback = json.loads(feedback_path.read_text())
    if not isinstance(feedback, dict):
        sys.exit("user_feedback.json root must be an object")

    info_suff = feedback.get("informationSufficiency")
    if info_suff not in satisfaction_buckets:
        sys.exit("informationSufficiency must use a supported bucket")
    earnings_inf = feedback.get("earningsInfluence")
    if earnings_inf not in influence_buckets:
        sys.exit("earningsInfluence must use a supported bucket")
    rating = feedback.get("overallConfidenceRating")
    if not isinstance(rating, (int, float)):
        sys.exit("overallConfidenceRating must be numeric")
    rating = int(round(float(rating)))
    if not 1 <= rating <= 10:
        sys.exit("overallConfidenceRating must be between 1 and 10")
    feedback_reason = feedback.get("reason")
    if not isinstance(feedback_reason, str) or not feedback_reason.strip():
        sys.exit("feedback reason must be non-empty")

    payload: dict[str, object] = {
        "information_sufficiency": info_suff,
        "earnings_influence": earnings_inf,
        "overall_confidence_rating": rating,
        "feedback_reason": feedback_reason.strip(),
    }
    would_act = feedback.get("wouldActOnIt")
    if would_act is not None:
        if not isinstance(would_act, bool):
            sys.exit("wouldActOnIt must be boolean")
        payload["would_act_on_it"] = "true" if would_act else "false"
    missing_info = feedback.get("missingInfoNote")
    if missing_info is not None:
        if not isinstance(missing_info, str):
            sys.exit("missingInfoNote must be a string")
        payload["missing_info_note"] = missing_info.strip()
    return payload


feedback = load_user_feedback()

# --- Build structured output ---
verifier_dir = Path(
    os.environ.get("VERIFIER_DIR")
    or os.environ.get("HARBOR_VERIFIER_DIR")
    or "/logs/verifier"
)
try:
    verifier_dir.mkdir(parents=True, exist_ok=True)
except OSError:
    verifier_dir = Path("/tmp/verifier_output")
    verifier_dir.mkdir(parents=True, exist_ok=True)

trend_labels = "; ".join(
    f"{tf}: {trend_summary.get(tf, '?')[:60]}" for tf in timeframes
)

source_artifacts = {
    "sentiment": str(path),
}
contexts = [
    {
        "key": "task_outcome.primary",
        "label": "Task outcome",
        "contextType": "task_outcome",
        "facets": [
            {
                "key": "outcome_status",
                "label": "Outcome status",
                "role": "primary",
                "kind": "categorical",
                "value": "passed",
            },
            {
                "key": "goal_completion_ratio",
                "label": "Goal completion ratio",
                "role": "score",
                "kind": "numerical",
                "value": 1.0,
            },
            {
                "key": "goal_completion_bucket",
                "label": "Goal completion bucket",
                "role": "primary",
                "kind": "categorical",
                "value": "complete",
            },
            {
                "key": "verifier_mode",
                "label": "Verifier mode",
                "role": "evidence",
                "kind": "categorical",
                "value": "artifact_exact",
            },
            {
                "key": "primary_failure_reason",
                "label": "Primary failure reason",
                "role": "primary",
                "kind": "categorical",
                "value": "none",
            },
            {
                "key": "outcome_explanation",
                "label": "Outcome explanation",
                "role": "explanation",
                "kind": "textual",
                "value": f"Researched MU in Stocks app, sentiment: {sentiment} (confidence {confidence}/10).",
            },
            {
                "key": "completion_evidence",
                "label": "Completion evidence",
                "role": "evidence",
                "kind": "textual",
                "value": str(path),
            },
        ],
    },
    {
        "key": "goal_component.viewed_chart",
        "label": "Viewed stock chart",
        "contextType": "goal_component",
        "facets": [
            {
                "key": "goal_component_key",
                "label": "Goal component key",
                "role": "evidence",
                "kind": "categorical",
                "value": "viewed_chart",
            },
            {
                "key": "goal_component_label",
                "label": "Goal component label",
                "role": "evidence",
                "kind": "textual",
                "value": "View MU chart across multiple timeframes",
            },
            {
                "key": "goal_component_status",
                "label": "Goal component status",
                "role": "primary",
                "kind": "categorical",
                "value": "passed",
            },
            {
                "key": "goal_component_weight",
                "label": "Goal component weight",
                "role": "score",
                "kind": "numerical",
                "value": 0.3,
            },
            {
                "key": "goal_component_required",
                "label": "Goal component required",
                "role": "evidence",
                "kind": "categorical",
                "value": "true",
            },
            {
                "key": "goal_component_evidence",
                "label": "Goal component evidence",
                "role": "explanation",
                "kind": "textual",
                "value": f"Timeframes checked: {', '.join(timeframes)}. Trends: {trend_labels}.",
            },
        ],
    },
    {
        "key": "goal_component.sentiment_decision",
        "label": "Sentiment decision",
        "contextType": "goal_component",
        "facets": [
            {
                "key": "goal_component_key",
                "label": "Goal component key",
                "role": "evidence",
                "kind": "categorical",
                "value": "sentiment_decision",
            },
            {
                "key": "goal_component_label",
                "label": "Goal component label",
                "role": "evidence",
                "kind": "textual",
                "value": "Form and report buy/sell/hold sentiment with reasoning",
            },
            {
                "key": "goal_component_status",
                "label": "Goal component status",
                "role": "primary",
                "kind": "categorical",
                "value": "passed",
            },
            {
                "key": "goal_component_weight",
                "label": "Goal component weight",
                "role": "score",
                "kind": "numerical",
                "value": 0.7,
            },
            {
                "key": "goal_component_required",
                "label": "Goal component required",
                "role": "evidence",
                "kind": "categorical",
                "value": "true",
            },
            {
                "key": "goal_component_evidence",
                "label": "Goal component evidence",
                "role": "explanation",
                "kind": "textual",
                "value": f"Sentiment: {sentiment}, confidence: {confidence}/10.",
            },
        ],
    },
    {
        "key": "decision.sentiment",
        "label": f"Sentiment: {sentiment.upper()}",
        "contextType": "decision",
        "facets": [
            {
                "key": "decision_outcome",
                "label": "Decision outcome",
                "role": "primary",
                "kind": "categorical",
                "value": sentiment,
            },
            {
                "key": "basis_primary",
                "label": "Primary basis",
                "role": "primary",
                "kind": "categorical",
                "value": "chart_and_earnings",
            },
            {
                "key": "decision_subject_id",
                "label": "Decision subject ID",
                "role": "evidence",
                "kind": "categorical",
                "value": "MU",
            },
            {
                "key": "decision_subject_label",
                "label": "Decision subject label",
                "role": "evidence",
                "kind": "textual",
                "value": "Micron Technology (MU)",
            },
            {
                "key": "decision_confidence",
                "label": "Decision confidence",
                "role": "score",
                "kind": "numerical",
                "value": confidence,
            },
            {
                "key": "reason",
                "label": "Reason",
                "role": "explanation",
                "kind": "textual",
                "value": reasoning.strip(),
            },
        ],
    },
    {
        "key": "persona_alignment.primary",
        "label": "Persona alignment",
        "contextType": "persona_alignment",
        "facets": [
            {
                "key": "persona_alignment_status",
                "label": "Persona alignment status",
                "role": "primary",
                "kind": "categorical",
                "value": "aligned",
            },
            {
                "key": "persona_preference_axis_primary",
                "label": "Primary preference axis",
                "role": "primary",
                "kind": "categorical",
                "value": "risk_tolerance",
            },
            {
                "key": "persona_alignment_explanation",
                "label": "Persona alignment explanation",
                "role": "explanation",
                "kind": "textual",
                "value": reasoning.strip(),
            },
            {
                "key": "persona_alignment_score",
                "label": "Persona alignment score",
                "role": "score",
                "kind": "numerical",
                "value": 1.0,
            },
        ],
    },
    {
        "key": "decision_process.primary",
        "label": "Decision process",
        "contextType": "decision_process",
        "facets": [
            {
                "key": "exploration_style",
                "label": "Exploration style",
                "role": "primary",
                "kind": "categorical",
                "value": "chart_news_earnings",
            },
            {
                "key": "process_notes",
                "label": "Process notes",
                "role": "explanation",
                "kind": "textual",
                "value": (
                    f"Checked {len(timeframes)} timeframes ({', '.join(timeframes)}), "
                    f"read {len(news)} news article(s), combined with earnings context. "
                    f"Final sentiment: {sentiment} (confidence {confidence}/10)."
                ),
            },
        ],
    },
]

if feedback is not None:
    source_artifacts["userFeedback"] = str(feedback_path)
    feedback_facets = [
        {
            "key": "overall_confidence_rating",
            "label": "Overall confidence rating",
            "role": "score",
            "kind": "numerical",
            "value": feedback["overall_confidence_rating"],
        },
        {
            "key": "feedback_reason",
            "label": "Feedback reason",
            "role": "explanation",
            "kind": "textual",
            "value": feedback["feedback_reason"],
        },
        {
            "key": "information_sufficiency",
            "label": "Information sufficiency",
            "role": "evidence",
            "kind": "categorical",
            "value": feedback["information_sufficiency"],
        },
        {
            "key": "earnings_influence",
            "label": "Earnings influence",
            "role": "evidence",
            "kind": "categorical",
            "value": feedback["earnings_influence"],
        },
    ]
    if "would_act_on_it" in feedback:
        feedback_facets.append(
            {
                "key": "would_act_on_it",
                "label": "Would act on it",
                "role": "evidence",
                "kind": "categorical",
                "value": feedback["would_act_on_it"],
            }
        )
    if "missing_info_note" in feedback:
        feedback_facets.append(
            {
                "key": "missing_info_note",
                "label": "Missing info note",
                "role": "explanation",
                "kind": "textual",
                "value": feedback["missing_info_note"],
            }
        )
    contexts.append(
        {
            "key": "user_feedback.primary",
            "label": "User feedback",
            "contextType": "user_feedback",
            "facets": feedback_facets,
        }
    )

(verifier_dir / "structured_output.json").write_text(
    json.dumps(
        {
            "schemaVersion": "1.0",
            "artifactType": "matraix.trial_evaluation",
            "taskType": "os-app",
            "presenceCheck": {
                "passed": True,
                "requiredArtifacts": ["sentiment.json"],
                "missingArtifacts": [],
            },
            "sourceArtifacts": source_artifacts,
            "contexts": contexts,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
PY
py_exit=$?
set -e

if [ $py_exit -eq 0 ]; then
  printf '1\n' > "${VERIFIER_DIR}/reward.txt"
else
  printf '0\n' > "${VERIFIER_DIR}/reward.txt"
fi
