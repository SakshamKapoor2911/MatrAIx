#!/usr/bin/env python3
"""V1 Amazon persona validation on temporal rating holdouts.

This script does not call an LLM. It prepares and scores the simple V1
evaluation:

1. assign users to loose cohorts from construction-split rating behavior,
2. write product-context-only prediction targets from validation_reviews,
3. score built-in non-personalized baselines and optional persona predictions,
4. report MAE and within-1-star accuracy by cohort.

The main persona-prediction input should be the blind target file written here.
It intentionally excludes labels and held-out review title/text so the task
stays product context only.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DEFAULT_HISTORY_PATH = (
    BASE_DIR
    / "raw"
    / "amazon_reviews_2023"
    / "persona_dimension_inference"
    / "user_histories.jsonl"
)
DEFAULT_OUTPUT_DIR = (
    BASE_DIR
    / "raw"
    / "amazon_reviews_2023"
    / "persona_rating_holdout_eval"
)


COHORT_ORDER = ("harsh_low", "high_variance", "mostly_5", "balanced_mixed")


def log(message: str) -> None:
    print(f"[amazon_persona_rating_eval] {message}", flush=True)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def iter_jsonl_or_gz(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    ensure_dir(path.parent)
    count = 0
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def blind_target(target: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in target.items()
        if key not in {"true_rating", "cohort"}
    }


def float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed):
        return None
    return parsed


def clamp_rating(value: float) -> float:
    return min(5.0, max(1.0, value))


def rating_key(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def population_std(values: list[float]) -> float | None:
    if not values:
        return None
    value_mean = sum(values) / len(values)
    return math.sqrt(sum((value - value_mean) ** 2 for value in values) / len(values))


def entropy_from_counts(counts: dict[str, int]) -> float:
    total = sum(counts.values())
    if not total:
        return 0.0
    entropy = 0.0
    for count in counts.values():
        if count:
            probability = count / total
            entropy -= probability * math.log2(probability)
    return entropy


def ratings_from_reviews(reviews: list[dict[str, Any]]) -> list[float]:
    ratings = []
    for review in reviews:
        rating = float_or_none(review.get("rating"))
        if rating is not None:
            ratings.append(rating)
    return ratings


def rating_counts(ratings: list[float]) -> dict[str, int]:
    counts = {str(value): 0 for value in range(1, 6)}
    for rating in ratings:
        rounded = int(round(rating))
        if 1 <= rounded <= 5:
            counts[str(rounded)] = counts.get(str(rounded), 0) + 1
        else:
            counts[rating_key(rating)] = counts.get(rating_key(rating), 0) + 1
    return counts


def user_rating_stats(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    ratings = ratings_from_reviews(reviews)
    counts = rating_counts(ratings)
    rating_count = len(ratings)
    share_5 = counts.get("5", 0) / rating_count if rating_count else 0.0
    share_1_2 = (counts.get("1", 0) + counts.get("2", 0)) / rating_count if rating_count else 0.0
    return {
        "rating_count": rating_count,
        "mean_rating": mean(ratings),
        "std_rating": population_std(ratings),
        "rating_counts": counts,
        "rating_share_5": share_5,
        "rating_share_1_2": share_1_2,
        "rating_share_non5": 1.0 - share_5 if rating_count else 0.0,
        "rating_entropy": entropy_from_counts(counts),
        "distinct_rating_count": sum(1 for count in counts.values() if count > 0),
    }


def assign_cohort(stats: dict[str, Any], args: argparse.Namespace) -> str:
    """Assign one loose cohort using deterministic precedence."""
    mean_rating = stats.get("mean_rating")
    std_rating = stats.get("std_rating") or 0.0
    share_5 = stats.get("rating_share_5") or 0.0
    share_non5 = stats.get("rating_share_non5") or 0.0
    share_1_2 = stats.get("rating_share_1_2") or 0.0

    # Precedence matters: harsh/high-variance users can also have many 5-star
    # reviews, so keep them out of the mostly-5 bucket when the stronger signal
    # is a meaningful low-rating or variance pattern.
    if (
        mean_rating is not None
        and mean_rating <= args.harsh_mean_max
        or share_1_2 >= args.harsh_share_1_2_min
    ):
        return "harsh_low"
    if std_rating >= args.high_variance_std_min or share_non5 >= args.high_variance_non5_min:
        return "high_variance"
    if share_5 >= args.mostly_5_share_min:
        return "mostly_5"
    return "balanced_mixed"


def product_context_from_review(review: dict[str, Any]) -> dict[str, Any]:
    metadata = review.get("product_metadata")
    product: dict[str, Any] = {}
    if isinstance(metadata, dict):
        title = metadata.get("title")
        if title:
            product["product_title"] = title
        main_category = metadata.get("main_category")
        if main_category:
            product["main_category"] = main_category
        source_category = metadata.get("source_category")
        if source_category:
            product["source_category"] = source_category
        categories_json = metadata.get("categories_json")
        if categories_json:
            try:
                categories = json.loads(categories_json)
            except (TypeError, ValueError):
                categories = None
            if categories:
                product["category_path"] = categories
    product.setdefault("source_category", review.get("category"))
    product["parent_asin"] = review.get("parent_asin")
    product["asin"] = review.get("asin")
    product["review_date"] = review.get("date")
    return {key: value for key, value in product.items() if value not in (None, "", [])}


def load_histories(path: Path, args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    users = []
    targets = []
    train_category_ratings: dict[str, list[float]] = defaultdict(list)
    global_train_ratings: list[float] = []

    for row in iter_jsonl_or_gz(path):
        user_id = str(row.get("user_id") or "")
        if not user_id:
            continue
        construction_reviews = row.get("reviews") or []
        validation_reviews = row.get("validation_reviews") or []
        train_stats = user_rating_stats(construction_reviews)
        validation_stats = user_rating_stats(validation_reviews)
        if train_stats["rating_count"] < args.min_train_ratings:
            continue
        if validation_stats["rating_count"] < args.min_validation_ratings:
            continue
        cohort = assign_cohort(train_stats, args)
        user = {
            "user_id": user_id,
            "cohort": cohort,
            "review_count": len(construction_reviews),
            "validation_review_count": len(validation_reviews),
            "category_count": len(row.get("categories") or []),
            "validation_category_count": len(row.get("validation_categories") or []),
            "train_rating_stats": train_stats,
            "validation_rating_stats": validation_stats,
        }
        users.append(user)

        for review in construction_reviews:
            rating = float_or_none(review.get("rating"))
            category = str(review.get("category") or "Unknown")
            if rating is not None:
                global_train_ratings.append(rating)
                train_category_ratings[category].append(rating)

        for validation_index, review in enumerate(validation_reviews, start=1):
            true_rating = float_or_none(review.get("rating"))
            if true_rating is None:
                continue
            target_id = f"{user_id}::v{validation_index:06d}"
            targets.append(
                {
                    "target_id": target_id,
                    "user_id": user_id,
                    "cohort": cohort,
                    "validation_index": validation_index,
                    "true_rating": true_rating,
                    "product_context": product_context_from_review(review),
                }
            )

    priors = {
        "global_mean_rating": mean(global_train_ratings),
        "category_mean_rating": {
            category: category_mean
            for category, ratings in sorted(train_category_ratings.items())
            if (category_mean := mean(ratings)) is not None
        },
    }
    return users, targets, priors


def sampled_users(users: list[dict[str, Any]], per_cohort: int, seed: int) -> list[dict[str, Any]]:
    if per_cohort <= 0:
        return users
    rng = random.Random(seed)
    selected = []
    for cohort in COHORT_ORDER:
        cohort_users = [user for user in users if user["cohort"] == cohort]
        cohort_users = sorted(cohort_users, key=lambda row: row["user_id"])
        if len(cohort_users) > per_cohort:
            cohort_users = rng.sample(cohort_users, per_cohort)
            cohort_users = sorted(cohort_users, key=lambda row: row["user_id"])
        selected.extend(cohort_users)
    return selected


def filter_targets_for_users(targets: list[dict[str, Any]], users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected_user_ids = {user["user_id"] for user in users}
    return [target for target in targets if target["user_id"] in selected_user_ids]


def load_predictions(path: Path) -> dict[str, float]:
    predictions = {}
    for row in iter_jsonl_or_gz(path):
        target_id = row.get("target_id")
        prediction = float_or_none(
            row.get("predicted_rating", row.get("prediction", row.get("rating")))
        )
        if not target_id or prediction is None:
            continue
        predictions[str(target_id)] = clamp_rating(prediction)
    return predictions


def build_baseline_predictions(
    targets: list[dict[str, Any]],
    priors: dict[str, Any],
) -> dict[str, dict[str, float]]:
    global_mean = float_or_none(priors.get("global_mean_rating")) or 5.0
    category_means = priors.get("category_mean_rating") or {}
    baselines: dict[str, dict[str, float]] = {
        "always_5": {},
        "global_mean": {},
        "category_mean": {},
    }
    for target in targets:
        target_id = target["target_id"]
        category = str((target.get("product_context") or {}).get("source_category") or "Unknown")
        baselines["always_5"][target_id] = 5.0
        baselines["global_mean"][target_id] = clamp_rating(global_mean)
        baselines["category_mean"][target_id] = clamp_rating(
            float_or_none(category_means.get(category)) or global_mean
        )
    return baselines


def metric_row(targets: list[dict[str, Any]], predictions: dict[str, float]) -> dict[str, Any]:
    errors = []
    within_1 = 0
    scored = 0
    missing = 0
    for target in targets:
        prediction = predictions.get(target["target_id"])
        if prediction is None:
            missing += 1
            continue
        true_rating = float(target["true_rating"])
        error = abs(clamp_rating(prediction) - true_rating)
        errors.append(error)
        scored += 1
        if error <= 1.0:
            within_1 += 1
    return {
        "targets": len(targets),
        "scored": scored,
        "missing": missing,
        "mae": sum(errors) / len(errors) if errors else None,
        "within_1_rate": within_1 / scored if scored else None,
    }


def evaluate_method(
    method_name: str,
    targets: list[dict[str, Any]],
    predictions: dict[str, float],
) -> dict[str, Any]:
    cohort_metrics = {}
    for cohort in COHORT_ORDER:
        cohort_targets = [target for target in targets if target["cohort"] == cohort]
        cohort_metrics[cohort] = metric_row(cohort_targets, predictions)

    user_metrics = {}
    for user_id in sorted({target["user_id"] for target in targets}):
        user_targets = [target for target in targets if target["user_id"] == user_id]
        user_metrics[user_id] = metric_row(user_targets, predictions)

    valid_user_maes = [
        metrics["mae"]
        for metrics in user_metrics.values()
        if metrics.get("mae") is not None
    ]
    valid_user_within_1 = [
        metrics["within_1_rate"]
        for metrics in user_metrics.values()
        if metrics.get("within_1_rate") is not None
    ]
    return {
        "method": method_name,
        "micro": metric_row(targets, predictions),
        "macro_user": {
            "users": len(user_metrics),
            "mae": sum(valid_user_maes) / len(valid_user_maes) if valid_user_maes else None,
            "within_1_rate": (
                sum(valid_user_within_1) / len(valid_user_within_1)
                if valid_user_within_1
                else None
            ),
        },
        "by_cohort": cohort_metrics,
        "by_user": user_metrics,
    }


def average_user_stat(users: list[dict[str, Any]], split: str, stat: str) -> float | None:
    values = [
        value
        for user in users
        if (value := user.get(f"{split}_rating_stats", {}).get(stat)) is not None
    ]
    return sum(values) / len(values) if values else None


def aggregate_rating_counts(users: list[dict[str, Any]], split: str) -> dict[str, int]:
    counts = {str(value): 0 for value in range(1, 6)}
    for user in users:
        for rating, count in user.get(f"{split}_rating_stats", {}).get("rating_counts", {}).items():
            counts[str(rating)] = counts.get(str(rating), 0) + int(count or 0)
    return counts


def cohort_summary(users: list[dict[str, Any]], targets: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {}
    target_counts_by_user = defaultdict(int)
    for target in targets:
        target_counts_by_user[target["user_id"]] += 1
    for cohort in COHORT_ORDER:
        cohort_users = [user for user in users if user["cohort"] == cohort]
        user_ids = {user["user_id"] for user in cohort_users}
        summary[cohort] = {
            "users": len(cohort_users),
            "targets": sum(count for user_id, count in target_counts_by_user.items() if user_id in user_ids),
            "train_mean_rating_avg_user": average_user_stat(cohort_users, "train", "mean_rating"),
            "train_std_rating_avg_user": average_user_stat(cohort_users, "train", "std_rating"),
            "train_share_5_avg_user": average_user_stat(cohort_users, "train", "rating_share_5"),
            "validation_mean_rating_avg_user": average_user_stat(
                cohort_users,
                "validation",
                "mean_rating",
            ),
            "validation_share_5_avg_user": average_user_stat(
                cohort_users,
                "validation",
                "rating_share_5",
            ),
            "train_rating_counts": aggregate_rating_counts(cohort_users, "train"),
            "validation_rating_counts": aggregate_rating_counts(cohort_users, "validation"),
        }
    return summary


def pct(value: Any) -> str:
    if value is None:
        return ""
    return f"{float(value) * 100:.1f}%"


def num(value: Any, digits: int = 4) -> str:
    if value is None:
        return ""
    return f"{float(value):.{digits}f}"


def render_markdown(summary: dict[str, Any], metrics: list[dict[str, Any]]) -> str:
    lines = [
        "# Amazon Persona Rating Holdout V1",
        "",
        "## Cohorts",
        "",
        "| Cohort | Users | Targets | Train mean | Train std | Train %5 | Validation mean | Validation %5 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for cohort in COHORT_ORDER:
        row = summary["cohorts"][cohort]
        lines.append(
            "| "
            + " | ".join(
                [
                    cohort,
                    f"{row['users']:,}",
                    f"{row['targets']:,}",
                    num(row["train_mean_rating_avg_user"]),
                    num(row["train_std_rating_avg_user"]),
                    pct(row["train_share_5_avg_user"]),
                    num(row["validation_mean_rating_avg_user"]),
                    pct(row["validation_share_5_avg_user"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Metrics",
            "",
            "| Method | Micro MAE | Micro within-1 | Macro-user MAE | Macro-user within-1 |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for result in metrics:
        lines.append(
            "| "
            + " | ".join(
                [
                    result["method"],
                    num(result["micro"]["mae"]),
                    pct(result["micro"]["within_1_rate"]),
                    num(result["macro_user"]["mae"]),
                    pct(result["macro_user"]["within_1_rate"]),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Metrics By Cohort", ""])
    for result in metrics:
        lines.extend(
            [
                f"### {result['method']}",
                "",
                "| Cohort | Targets | Scored | MAE | Within-1 |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for cohort in COHORT_ORDER:
            row = result["by_cohort"][cohort]
            lines.append(
                "| "
                + " | ".join(
                    [
                        cohort,
                        f"{row['targets']:,}",
                        f"{row['scored']:,}",
                        num(row["mae"]),
                        pct(row["within_1_rate"]),
                    ]
                )
                + " |"
            )
        lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare and score V1 Amazon persona temporal rating holdout evaluation."
    )
    parser.add_argument("--user-histories", type=Path, default=DEFAULT_HISTORY_PATH)
    parser.add_argument("--predictions", type=Path, help="Optional persona prediction JSONL.")
    parser.add_argument("--prediction-method-name", default="persona_predictions")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--targets-output", type=Path)
    parser.add_argument("--blind-targets-output", type=Path)
    parser.add_argument("--users-output", type=Path)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--report-output", type=Path)
    parser.add_argument("--sample-users-per-cohort", type=int, default=0)
    parser.add_argument("--sample-seed", type=int, default=13)
    parser.add_argument("--min-train-ratings", type=int, default=30)
    parser.add_argument("--min-validation-ratings", type=int, default=1)
    parser.add_argument("--mostly-5-share-min", type=float, default=0.90)
    parser.add_argument("--high-variance-std-min", type=float, default=1.0)
    parser.add_argument("--high-variance-non5-min", type=float, default=0.25)
    parser.add_argument("--harsh-mean-max", type=float, default=3.8)
    parser.add_argument("--harsh-share-1-2-min", type=float, default=0.15)
    parser.add_argument(
        "--no-baselines",
        action="store_true",
        help="Only score --predictions; do not score built-in baselines.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.user_histories.exists():
        raise FileNotFoundError(f"User histories not found: {args.user_histories}")

    output_dir = args.output_dir
    targets_output = args.targets_output or output_dir / "targets.jsonl"
    blind_targets_output = args.blind_targets_output or output_dir / "prediction_targets.jsonl"
    users_output = args.users_output or output_dir / "users.jsonl"
    summary_output = args.summary_output or output_dir / "summary.json"
    report_output = args.report_output or output_dir / "report.md"

    users, targets, priors = load_histories(args.user_histories, args)
    users = sampled_users(users, args.sample_users_per_cohort, args.sample_seed)
    targets = filter_targets_for_users(targets, users)

    metrics = []
    if not args.no_baselines:
        for method, predictions in build_baseline_predictions(targets, priors).items():
            metrics.append(evaluate_method(method, targets, predictions))
    if args.predictions:
        metrics.append(
            evaluate_method(
                args.prediction_method_name,
                targets,
                load_predictions(args.predictions),
            )
        )

    summary = {
        "user_histories": str(args.user_histories),
        "predictions": str(args.predictions) if args.predictions else None,
        "thresholds": {
            "min_train_ratings": args.min_train_ratings,
            "min_validation_ratings": args.min_validation_ratings,
            "mostly_5_share_min": args.mostly_5_share_min,
            "high_variance_std_min": args.high_variance_std_min,
            "high_variance_non5_min": args.high_variance_non5_min,
            "harsh_mean_max": args.harsh_mean_max,
            "harsh_share_1_2_min": args.harsh_share_1_2_min,
        },
        "priors": priors,
        "cohorts": cohort_summary(users, targets),
        "metrics": metrics,
    }

    written_users = write_jsonl(users_output, users)
    written_targets = write_jsonl(targets_output, targets)
    written_blind_targets = write_jsonl(
        blind_targets_output,
        (blind_target(target) for target in targets),
    )
    write_json(summary_output, summary)
    ensure_dir(report_output.parent)
    report_output.write_text(render_markdown(summary, metrics) + "\n", encoding="utf-8")
    log(
        f"Wrote {written_users:,} users, {written_targets:,} scoring targets, "
        f"{written_blind_targets:,} blind targets, "
        f"summary {summary_output}, report {report_output}"
    )


if __name__ == "__main__":
    main()
