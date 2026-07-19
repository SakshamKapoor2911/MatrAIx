#!/usr/bin/env python3
"""Validate and aggregate independent M1-M7 persona review JSON files."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

METRICS = (
    "M1_value",
    "M2_evidence",
    "M3_description",
    "M4_overclaim",
    "M5_coverage",
    "M6_consistency",
    "M7_overall",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument(
        "--expected-model",
        action="append",
        default=[],
        help="Requested model display name. Repeat for panel mode.",
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def load_reviews(path: Path) -> list[tuple[dict[str, Any], Path]]:
    if not path.is_dir():
        raise FileNotFoundError(f"Reviews directory not found: {path}")
    loaded: list[tuple[dict[str, Any], Path]] = []
    for review_path in sorted(path.rglob("*.json")):
        try:
            payload = json.loads(review_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid review JSON {review_path}: {error}") from error
        if not isinstance(payload, dict):
            raise ValueError(f"Review is not a JSON object: {review_path}")
        loaded.append((payload, review_path))
    if not loaded:
        raise ValueError(f"No review JSON files found under {path}")
    return loaded


def validate_score(metric: str, value: Any, path: Path) -> int | str:
    if metric == "M3_description" and value == "n/a":
        return value
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        raise ValueError(f"{path}: {metric}.score must be integer 1-5 (or M3 n/a), got {value!r}")
    return value


def validate_review(payload: dict[str, Any], path: Path) -> dict[str, Any]:
    persona_id = payload.get("persona_id")
    if not isinstance(persona_id, str) or not persona_id.strip():
        raise ValueError(f"{path}: missing persona_id")
    judge = payload.get("judge")
    if not isinstance(judge, dict):
        raise ValueError(f"{path}: missing judge object")
    requested_model = judge.get("requested_model")
    actual_model = judge.get("actual_model")
    if not isinstance(requested_model, str) or not requested_model.strip():
        raise ValueError(f"{path}: missing requested_model")
    if not isinstance(actual_model, str) or not actual_model.strip():
        raise ValueError(f"{path}: missing actual_model")

    audit = payload.get("audit")
    if not isinstance(audit, dict):
        raise ValueError(f"{path}: missing audit object")
    expected_count = audit.get("extracted_field_count")
    checked_count = audit.get("checked_field_count")
    if not isinstance(expected_count, int) or not isinstance(checked_count, int):
        raise ValueError(f"{path}: field counts must be integers")
    if checked_count != expected_count or audit.get("complete_field_pass") is not True:
        raise ValueError(
            f"{path}: incomplete field pass ({checked_count}/{expected_count}, "
            f"complete={audit.get('complete_field_pass')!r})"
        )

    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        raise ValueError(f"{path}: missing metrics object")
    normalized_scores: dict[str, int | str] = {}
    for metric in METRICS:
        entry = metrics.get(metric)
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: missing metric {metric}")
        reason = entry.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"{path}: {metric} has empty reason")
        normalized_scores[metric] = validate_score(metric, entry.get("score"), path)

    return {
        "payload": payload,
        "path": str(path),
        "persona_id": persona_id,
        "requested_model": requested_model,
        "actual_model": actual_model,
        "scores": normalized_scores,
    }


def unique_majority(scores: list[int]) -> int | None:
    counts = Counter(scores)
    ordered = counts.most_common()
    if not ordered:
        return None
    if len(ordered) == 1 or ordered[0][1] > ordered[1][1]:
        return ordered[0][0]
    return None


def metric_consensus(scores_by_model: dict[str, int | str]) -> dict[str, Any]:
    numeric = [score for score in scores_by_model.values() if isinstance(score, int)]
    if not numeric:
        return {
            "scores": scores_by_model,
            "majority_score": None,
            "median_score": "n/a",
            "min_score": "n/a",
            "max_score": "n/a",
            "range": "n/a",
            "exact_agreement": True,
            "disagreement": False,
        }
    score_range = max(numeric) - min(numeric)
    majority = unique_majority(numeric)
    return {
        "scores": scores_by_model,
        "majority_score": majority,
        "median_score": statistics.median(numeric),
        "min_score": min(numeric),
        "max_score": max(numeric),
        "range": score_range,
        "exact_agreement": len(set(numeric)) == 1,
        "disagreement": score_range >= 2 or majority is None,
    }


def load_manifest_ids(path: Path | None) -> set[str] | None:
    if path is None:
        return None
    ids: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid manifest JSON at {path}:{line_number}: {error}") from error
            persona_id = payload.get("persona_id")
            if not isinstance(persona_id, str):
                raise ValueError(f"Manifest row lacks persona_id at {path}:{line_number}")
            if persona_id in ids:
                raise ValueError(f"Duplicate persona_id in manifest: {persona_id}")
            ids.add(persona_id)
    return ids


def main() -> int:
    args = parse_args()
    reviews_path = args.reviews.resolve()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        if not args.overwrite:
            raise FileExistsError(f"Output directory is not empty: {output}; use --overwrite")
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    validated = [validate_review(payload, path) for payload, path in load_reviews(reviews_path)]
    expected_personas = load_manifest_ids(args.manifest.resolve() if args.manifest else None)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_requested_pairs: set[tuple[str, str]] = set()
    for review in validated:
        pair = (review["persona_id"], review["requested_model"])
        if pair in seen_requested_pairs:
            raise ValueError(f"Duplicate persona/requested-model review: {pair}")
        seen_requested_pairs.add(pair)
        grouped[review["persona_id"]].append(review)

    expected_models = list(dict.fromkeys(args.expected_model))
    per_persona: list[dict[str, Any]] = []
    recurring_issues: Counter[str] = Counter()
    model_metric_scores: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(list)
    )
    metric_agreement = Counter()

    for persona_id in sorted(grouped):
        reviews = grouped[persona_id]
        requested_present = {review["requested_model"] for review in reviews}
        actual_models = [review["actual_model"] for review in reviews]
        missing_models = [model for model in expected_models if model not in requested_present]
        duplicate_actual_models = sorted(
            model for model, count in Counter(actual_models).items() if count > 1
        )
        metrics: dict[str, Any] = {}
        disagreement_metrics: list[str] = []
        for metric in METRICS:
            scores_by_model = {
                review["requested_model"]: review["scores"][metric] for review in reviews
            }
            consensus = metric_consensus(scores_by_model)
            metrics[metric] = consensus
            if consensus["exact_agreement"]:
                metric_agreement[(metric, "exact")] += 1
            metric_agreement[(metric, "total")] += 1
            if consensus["disagreement"]:
                disagreement_metrics.append(metric)
            for review in reviews:
                score = review["scores"][metric]
                if isinstance(score, int):
                    model_metric_scores[review["actual_model"]][metric].append(score)

        for review in reviews:
            for finding in review["payload"].get("flagged_fields", []):
                if isinstance(finding, dict) and isinstance(finding.get("field_id"), str):
                    recurring_issues[finding["field_id"]] += 1

        needs_adjudication = bool(
            missing_models or duplicate_actual_models or disagreement_metrics
        )
        per_persona.append(
            {
                "persona_id": persona_id,
                "review_count": len(reviews),
                "requested_models": sorted(requested_present),
                "actual_models": actual_models,
                "missing_requested_models": missing_models,
                "duplicate_actual_models": duplicate_actual_models,
                "metrics": metrics,
                "needs_adjudication": needs_adjudication,
                "adjudication_reasons": {
                    "missing_requested_models": missing_models,
                    "duplicate_actual_models": duplicate_actual_models,
                    "disagreement_metrics": disagreement_metrics,
                },
            }
        )

    consensus_jsonl = output / "per_persona_consensus.jsonl"
    with consensus_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for row in per_persona:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    consensus_csv = output / "per_persona_consensus.csv"
    csv_fields = ["persona_id", "review_count", "needs_adjudication"]
    for metric in METRICS:
        csv_fields.extend(
            [f"{metric}_majority", f"{metric}_median", f"{metric}_range"]
        )
    with consensus_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for row in per_persona:
            flat: dict[str, Any] = {
                "persona_id": row["persona_id"],
                "review_count": row["review_count"],
                "needs_adjudication": row["needs_adjudication"],
            }
            for metric in METRICS:
                consensus = row["metrics"][metric]
                flat[f"{metric}_majority"] = consensus["majority_score"]
                flat[f"{metric}_median"] = consensus["median_score"]
                flat[f"{metric}_range"] = consensus["range"]
            writer.writerow(flat)

    reviewed_personas = set(grouped)
    missing_personas = sorted(expected_personas - reviewed_personas) if expected_personas else []
    unexpected_personas = sorted(reviewed_personas - expected_personas) if expected_personas else []
    model_summary: dict[str, Any] = {}
    for model, by_metric in sorted(model_metric_scores.items()):
        model_summary[model] = {
            metric: {
                "count": len(scores),
                "mean": sum(scores) / len(scores),
                "distribution": dict(sorted(Counter(scores).items())),
            }
            for metric, scores in by_metric.items()
        }

    agreement_summary = {
        metric: {
            "exact_count": metric_agreement[(metric, "exact")],
            "persona_count": metric_agreement[(metric, "total")],
            "exact_rate": (
                metric_agreement[(metric, "exact")]
                / metric_agreement[(metric, "total")]
                if metric_agreement[(metric, "total")]
                else None
            ),
        }
        for metric in METRICS
    }
    summary = {
        "schema_version": "1.0",
        "reviews_directory": str(reviews_path),
        "valid_review_count": len(validated),
        "reviewed_persona_count": len(per_persona),
        "expected_persona_count": len(expected_personas) if expected_personas else None,
        "missing_personas": missing_personas,
        "unexpected_personas": unexpected_personas,
        "expected_models": expected_models,
        "actual_models": sorted({review["actual_model"] for review in validated}),
        "personas_requiring_adjudication": sum(
            row["needs_adjudication"] for row in per_persona
        ),
        "agreement": agreement_summary,
        "by_actual_model": model_summary,
        "recurring_flagged_field_ids": recurring_issues.most_common(100),
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:  # noqa: BLE001 - CLI should fail with a concise message.
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
