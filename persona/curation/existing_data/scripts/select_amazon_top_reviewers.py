#!/usr/bin/env python3
"""Select top Amazon reviewers for staged persona inference.

The input is the user-level eligible-reviewer artifact produced by the Amazon
Reviews 2023 Modal/HuggingFace pipeline. This script ranks eligible users by
signals that should make persona extraction richer: review text volume,
text-review count, category breadth, history length, review count, and
verified-purchase share.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime
import json
import math
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DEFAULT_REPO_ID = "MatrAIx/MatrAIx"
DEFAULT_ARTIFACT = (
    "amazon/modal_artifacts/"
    "amazon_reviews_2018_2023_eligible_users_min30_verified70_text2000"
)
DEFAULT_OUTPUT_DIR = BASE_DIR / "outputs" / "amazon_reviews_2023" / "top_reviewers"

RANKING_WEIGHTS = {
    "text_chars": 0.35,
    "text_reviews": 0.20,
    "category_count": 0.20,
    "history_days": 0.15,
    "review_count": 0.05,
    "verified_share": 0.05,
}

OUTPUT_FIELDS = [
    "rank",
    "user_id",
    "user_bucket",
    "rich_persona_score",
    "review_count",
    "text_reviews",
    "text_chars",
    "chars_per_text_review",
    "category_count",
    "history_days",
    "history_years",
    "verified_share",
    "verified_count",
    "rating_count",
    "average_rating",
    "first_date",
    "last_date",
    "categories",
]

NUMERIC_FIELDS = [
    "review_count",
    "category_count",
    "history_days",
    "history_years",
    "text_chars",
    "text_reviews",
    "verified_share",
    "verified_count",
    "rating_count",
    "average_rating",
]


def json_safe(value: Any) -> Any:
    """Convert scalar-like values to JSON-safe Python values."""
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if hasattr(value, "tolist"):
        return json_safe(value.tolist())
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            return str(value)
    return value


def numeric_value(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(number) or math.isinf(number):
        return 0.0
    return number


def parse_iso_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    text = str(value)
    if "T" in text:
        text = text.split("T", 1)[0]
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def prepare_row(row: dict[str, Any]) -> dict[str, Any]:
    prepared = dict(row)
    for column in NUMERIC_FIELDS:
        prepared[column] = numeric_value(prepared.get(column))

    first_date = parse_iso_date(prepared.get("first_date"))
    last_date = parse_iso_date(prepared.get("last_date"))
    if first_date is not None and last_date is not None:
        computed_history_days = max((last_date - first_date).days, 0)
        prepared["history_days"] = max(
            prepared["history_days"],
            float(computed_history_days),
        )

    if prepared["text_reviews"] <= 0:
        prepared["text_reviews"] = prepared["review_count"]
    prepared["chars_per_text_review"] = round(
        prepared["text_chars"] / max(prepared["text_reviews"], 1),
        3,
    )
    if prepared["history_years"] <= 0 and prepared["history_days"] > 0:
        prepared["history_years"] = round(prepared["history_days"] / 365.25, 3)
    return prepared


def percentile_ranks(values: list[float]) -> list[float]:
    """Return pandas-like pct ranks with average tie handling."""
    if not values:
        return []

    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(indexed):
        end = position + 1
        while end < len(indexed) and indexed[end][1] == indexed[position][1]:
            end += 1
        average_rank = (position + 1 + end) / 2
        percentile = average_rank / len(indexed)
        for original_index, _value in indexed[position:end]:
            ranks[original_index] = percentile
        position = end
    return ranks


def rank_users(rows: Iterable[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    prepared_rows = [prepare_row(row) for row in rows]
    if not prepared_rows:
        return []

    scores = [0.0] * len(prepared_rows)
    for source_column, weight in RANKING_WEIGHTS.items():
        ranks = percentile_ranks(
            [numeric_value(row.get(source_column)) for row in prepared_rows]
        )
        for index, rank in enumerate(ranks):
            scores[index] += rank * weight

    for row, score in zip(prepared_rows, scores, strict=True):
        row["rich_persona_score"] = round(score, 6)

    ranked = sorted(
        prepared_rows,
        key=lambda row: (
            -numeric_value(row.get("rich_persona_score")),
            -numeric_value(row.get("text_chars")),
            -numeric_value(row.get("category_count")),
            -numeric_value(row.get("history_days")),
            -numeric_value(row.get("review_count")),
            -numeric_value(row.get("verified_share")),
            str(row.get("user_id") or ""),
        ),
    )

    selected = [dict(row) for row in ranked[:top_k]]
    for index, row in enumerate(selected, start=1):
        row["rank"] = index
    return selected


def quantile(values: list[float], q: float) -> float:
    cleaned = sorted(numeric_value(value) for value in values)
    if not cleaned:
        return 0.0
    if len(cleaned) == 1:
        return float(cleaned[0])
    position = q * (len(cleaned) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(cleaned[lower])
    fraction = position - lower
    return float(cleaned[lower] * (1 - fraction) + cleaned[upper] * fraction)


def quantiles(rows: list[dict[str, Any]], metric: str) -> dict[str, float]:
    values = [numeric_value(row.get(metric)) for row in rows]
    return {str(q): quantile(values, q) for q in [0, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0]}


def output_stem(selected_count: int) -> str:
    return f"amazon_top_{selected_count:05d}_rich_persona_reviewers_2018_2023"


def write_outputs(
    selected: list[dict[str, Any]],
    source_count: int,
    output_dir: Path,
    repo_id: str,
    artifact: str,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = output_stem(len(selected))
    jsonl_path = output_dir / f"{stem}.jsonl"
    csv_path = output_dir / f"{stem}.csv"
    ids_path = output_dir / (
        f"amazon_top_{len(selected):05d}_rich_persona_reviewer_ids_2018_2023.txt"
    )
    markdown_path = output_dir / f"{stem}.md"
    summary_json_path = output_dir / f"{stem}_summary.json"

    records = []
    for selected_row in selected:
        row = {field: json_safe(selected_row.get(field)) for field in OUTPUT_FIELDS}
        records.append(row)

    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in records:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    csv_records = []
    for row in records:
        csv_row = dict(row)
        if isinstance(csv_row.get("categories"), list):
            csv_row["categories"] = "|".join(
                str(item) for item in csv_row["categories"]
            )
        csv_records.append(csv_row)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(csv_records)

    ids_path.write_text(
        "\n".join(str(row["user_id"]) for row in records if row.get("user_id")) + "\n",
        encoding="utf-8",
    )

    metrics = [
        "review_count",
        "text_reviews",
        "text_chars",
        "category_count",
        "history_days",
        "verified_share",
        "rich_persona_score",
    ]
    summary = {
        "source_dataset": repo_id,
        "source_artifact": artifact,
        "source_rows": int(source_count),
        "selected_rows": int(len(selected)),
        "eligibility_filter_in_source_artifact": {
            "time_window": "2018-2023",
            "review_count": ">= 30",
            "verified_share": ">= 0.70",
            "text_chars": ">= 2000",
        },
        "ranking_weights": RANKING_WEIGHTS,
        "selected_quantiles": {metric: quantiles(selected, metric) for metric in metrics},
        "outputs": {
            "jsonl": str(jsonl_path),
            "csv": str(csv_path),
            "user_ids": str(ids_path),
            "markdown": str(markdown_path),
            "summary": str(summary_json_path),
        },
    }
    summary_json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(
        render_markdown(selected, source_count, repo_id, artifact, summary),
        encoding="utf-8",
    )
    return summary


def render_markdown(
    selected: list[dict[str, Any]],
    source_count: int,
    repo_id: str,
    artifact: str,
    summary: dict[str, Any],
) -> str:
    count_label = f"{len(selected):,}"
    lines = [
        f"# Amazon Top {count_label} Rich Persona Reviewers",
        "",
        (
            "This file documents a reusable Amazon reviewer pool for persona "
            "inference. It is intended for staged inference runs when running "
            "all eligible users at once is too expensive."
        ),
        "",
        "## Source",
        "",
        f"- Hugging Face dataset: `{repo_id}`",
        f"- Source artifact: `{artifact}`",
        "- Source artifact time window: `2018-2023`",
        (
            "- Source eligibility filter: `review_count >= 30`, "
            "`verified_share >= 0.70`, `text_chars >= 2000`"
        ),
        f"- Eligible rows loaded: `{source_count:,}`",
        f"- Selected rows: `{len(selected):,}`",
        "",
        "## Output Files",
        "",
        (
            "- `amazon_top_<N>_rich_persona_reviewer_ids_2018_2023.txt`: "
            "one user ID per line for retrieval/inference jobs."
        ),
        (
            "- `amazon_top_<N>_rich_persona_reviewers_2018_2023.jsonl`: "
            "ranked users with scoring metrics and category metadata."
        ),
        (
            "- `amazon_top_<N>_rich_persona_reviewers_2018_2023.csv`: "
            "same ranked table in CSV form for quick inspection."
        ),
        "",
        "## Ranking Score",
        "",
        (
            "The ranking score is a weighted sum of percentile ranks across "
            "richness signals. Percentile ranks are used because Amazon review "
            "activity is heavy-tailed."
        ),
        "",
        "| Signal | Weight | Why it matters |",
        "|---|---:|---|",
        (
            "| `text_chars` | 0.35 | More written evidence for values, "
            "preferences, routines, and decision style. |"
        ),
        "| `text_reviews` | 0.20 | More distinct text-bearing observations. |",
        (
            "| `category_count` | 0.20 | Broader life/product coverage, "
            "supporting richer cross-domain personas. |"
        ),
        (
            "| `history_days` | 0.15 | Longer temporal history, reducing "
            "one-off or short-burst behavior. |"
        ),
        (
            "| `review_count` | 0.05 | More total rating/review events, "
            "including rating-only behavior. |"
        ),
        "| `verified_share` | 0.05 | Higher purchase-verification reliability. |",
        "",
        "## Selected Pool Summary",
        "",
        "| Metric | Min | P25 | Median | P75 | P90 | P99 | Max |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for metric in [
        "review_count",
        "text_reviews",
        "text_chars",
        "category_count",
        "history_days",
        "verified_share",
        "rich_persona_score",
    ]:
        values = summary["selected_quantiles"][metric]
        lines.append(
            f"| `{metric}` | {values['0']:.3f} | {values['0.25']:.3f} | "
            f"{values['0.5']:.3f} | {values['0.75']:.3f} | "
            f"{values['0.9']:.3f} | {values['0.99']:.3f} | "
            f"{values['1.0']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Top 20 Preview",
            "",
            (
                "| Rank | User ID | Score | Reviews | Text reviews | Text chars | "
                "Categories | History days | Verified share |"
            ),
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in selected[:20]:
        lines.append(
            f"| {int(numeric_value(row.get('rank')))} | `{row.get('user_id')}` | "
            f"{numeric_value(row.get('rich_persona_score')):.4f} | "
            f"{int(numeric_value(row.get('review_count')))} | "
            f"{int(numeric_value(row.get('text_reviews')))} | "
            f"{int(numeric_value(row.get('text_chars')))} | "
            f"{int(numeric_value(row.get('category_count')))} | "
            f"{numeric_value(row.get('history_days')):.1f} | "
            f"{numeric_value(row.get('verified_share')):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Reproducibility Note",
            "",
            (
                "The selected users are ranked from the existing eligible-user "
                "summary artifact, not by reading raw review text or calling an "
                "LLM. This makes the list cheap to regenerate and suitable as a "
                "shared inference queue."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def load_eligible_users(
    repo_id: str,
    repo_type: str,
    artifact: str,
    token: str | bool | None,
) -> list[dict[str, Any]]:
    try:
        from huggingface_hub import hf_hub_download
        import pyarrow.parquet as pq
    except ImportError as err:
        raise RuntimeError(
            "Selecting reviewers from HuggingFace Parquet artifacts requires "
            "optional dependencies. Install with: pip install -e '.[amazon-modal]'"
        ) from err

    rows: list[dict[str, Any]] = []
    for bucket_id in range(256):
        bucket = f"{bucket_id:02x}"
        filename = f"{artifact.rstrip('/')}/bucket={bucket}/eligible_users.parquet"
        local_path = hf_hub_download(
            repo_id=repo_id,
            repo_type=repo_type,
            filename=filename,
            token=token,
        )
        shard_rows = pq.read_table(local_path).to_pylist()
        for row in shard_rows:
            if "user_bucket" not in row:
                row["user_bucket"] = bucket
        rows.extend(shard_rows)
        if (bucket_id + 1) % 32 == 0:
            print(
                f"Loaded {bucket_id + 1}/256 buckets; {len(rows):,} rows",
                flush=True,
            )
    return rows


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--artifact", default=DEFAULT_ARTIFACT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--top-k", type=int, default=10_000)
    parser.add_argument("--repo-type", default="dataset")
    parser.add_argument(
        "--token",
        default=None,
        help="Optional HuggingFace token. If omitted, local HF auth is used.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    token: str | bool | None = args.token or None
    users = load_eligible_users(args.repo_id, args.repo_type, args.artifact, token=token)
    selected = rank_users(users, args.top_k)
    summary = write_outputs(
        selected,
        source_count=len(users),
        output_dir=args.output_dir,
        repo_id=args.repo_id,
        artifact=args.artifact,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
