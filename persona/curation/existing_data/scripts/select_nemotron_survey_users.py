#!/usr/bin/env python3
"""Select a diverse Nemotron user set for general survey simulations.

Unlike the domain-selection sample, this selector intentionally does not filter
for topical relevance. It chooses a deterministic 50-person population with
variation across demographic and life-context fields so survey experiments can
exercise a broad respondent mix.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import yaml


DEFAULT_CURATED_DIR = Path(
    "persona/curation/existing_data/raw/nemotron_personas_usa/curated_personas"
)
DEFAULT_OUTPUT_DIR = Path(
    "persona/curation/existing_data/outputs/nemotron_survey_selection"
)

AGE_BANDS = [
    (18, 24, "18-24"),
    (25, 34, "25-34"),
    (35, 44, "35-44"),
    (45, 54, "45-54"),
    (55, 64, "55-64"),
    (65, 120, "65+"),
]

VARIATION_WEIGHTS = {
    "age_band": 1.35,
    "gender": 1.15,
    "education_level": 1.05,
    "marital_status": 0.85,
    "occupation_group": 1.15,
    "state": 0.55,
}


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--curated-dir", type=Path, default=DEFAULT_CURATED_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--max-candidates", type=int, default=0, help="0 means all Nemotron YAML files.")
    return parser.parse_args(argv)


def stable_hash(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:16], 16)


def stable_unit(value: str) -> float:
    return stable_hash(value) / 0xFFFFFFFFFFFFFFFF


def compact(value: Any, max_chars: int = 220) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def age_band(age: Any) -> str:
    try:
        parsed = int(age)
    except (TypeError, ValueError):
        return "unknown"
    for low, high, label in AGE_BANDS:
        if low <= parsed <= high:
            return label
    return "unknown"


def occupation_group(occupation: str) -> str:
    text = (occupation or "unknown").lower()
    if any(token in text for token in ["software", "computer", "engineer", "data", "analyst"]):
        return "technology"
    if any(token in text for token in ["teacher", "professor", "education", "instructor", "librarian"]):
        return "education"
    if any(token in text for token in ["nurse", "physician", "medical", "therapist", "health"]):
        return "healthcare"
    if any(token in text for token in ["manager", "business", "sales", "marketing", "financial", "account"]):
        return "business"
    if any(token in text for token in ["artist", "designer", "writer", "actor", "musician", "producer"]):
        return "creative"
    if any(token in text for token in ["student", "not_in_workforce", "retired", "homemaker"]):
        return "nontraditional_or_student"
    if any(token in text for token in ["construction", "driver", "mechanic", "technician", "operator"]):
        return "trades_operations"
    if text == "unknown":
        return "unknown"
    return "other"


def load_persona(path: Path) -> dict[str, Any] | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict) or data.get("source") != "Nemotron":
        return None
    demographics = data.get("demographics") or {}
    location = demographics.get("location") or {}
    personas = data.get("personas") or {}
    attributes = data.get("attributes") or {}
    try:
        age = int(demographics.get("age"))
    except (TypeError, ValueError):
        return None
    if age < 18:
        return None
    occupation = str(demographics.get("occupation") or "unknown")
    record = {
        "file": path.name,
        "path": str(path),
        "id": str(data.get("id") or path.stem.removeprefix("Nemotron_")),
        "record_index": data.get("record_index"),
        "age": age,
        "age_band": age_band(age),
        "gender": demographics.get("gender") or "Unknown",
        "marital_status": demographics.get("marital_status") or "unknown",
        "education_level": demographics.get("education_level") or "unknown",
        "occupation": occupation,
        "occupation_group": occupation_group(occupation),
        "city": location.get("city") or "",
        "state": location.get("state") or "",
        "country": location.get("country") or "",
        "zipcode": str(location.get("zipcode") or ""),
        "core": compact(personas.get("core"), 260),
        "professional": compact(personas.get("professional"), 220),
        "hobbies": compact(attributes.get("hobbies"), 220),
        "skills": compact(attributes.get("skills"), 180),
    }
    return record


def load_candidates(curated_dir: Path, max_candidates: int) -> list[dict[str, Any]]:
    paths = sorted(curated_dir.glob("Nemotron_*.yaml"))
    if max_candidates > 0:
        paths = sorted(paths, key=lambda path: stable_hash(path.name))[:max_candidates]
    candidates = []
    for index, path in enumerate(paths, start=1):
        record = load_persona(path)
        if record is not None:
            candidates.append(record)
        if index % 10_000 == 0:
            print(f"Loaded {index:,}/{len(paths):,} files; valid candidates={len(candidates):,}", flush=True)
    return candidates


def diversity_score(candidate: dict[str, Any], selected: list[dict[str, Any]], counts: dict[str, Counter]) -> float:
    score = 0.0
    for key, weight in VARIATION_WEIGHTS.items():
        value = str(candidate.get(key) or "unknown")
        score += weight / (1 + counts[key][value])
    # Penalize duplicate exact occupations more strongly than broad occupation group.
    score += 0.8 / (1 + counts["occupation"][str(candidate.get("occupation") or "unknown")])
    # Small deterministic jitter prevents stable ties from overusing filename order.
    score += stable_unit(str(candidate.get("file"))) * 0.01
    return score


def select_diverse(candidates: list[dict[str, Any]], sample_size: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    remaining = list(candidates)
    counts = {key: Counter() for key in [*VARIATION_WEIGHTS, "occupation"]}
    while remaining and len(selected) < sample_size:
        best_index, _best_score = max(
            enumerate(remaining),
            key=lambda item: diversity_score(item[1], selected, counts),
        )
        chosen = remaining.pop(best_index)
        selected.append(chosen)
        for key in counts:
            counts[key][str(chosen.get(key) or "unknown")] += 1
    return selected


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def summary_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(key) or "unknown") for row in rows).items()))


def render_markdown(rows: list[dict[str, Any]], candidate_count: int) -> str:
    lines = [
        "# Nemotron Survey Use-Case Users",
        "",
        "This sample contains 50 Nemotron personas selected for general survey simulations.",
        "The selector does not use domain relevance keywords; it greedily maximizes variation across age band, gender, education, marital status, occupation group, and geography.",
        "",
        "## Summary",
        "",
        f"- Candidate personas scanned: `{candidate_count:,}`",
        f"- Selected personas: `{len(rows):,}`",
        "",
        "### Age Bands",
        "",
        "| Age band | Users |",
        "| --- | ---: |",
    ]
    for value, count in summary_counts(rows, "age_band").items():
        lines.append(f"| {value} | {count} |")
    lines.extend(["", "### Gender", "", "| Gender | Users |", "| --- | ---: |"])
    for value, count in summary_counts(rows, "gender").items():
        lines.append(f"| {value} | {count} |")
    lines.extend(["", "### Education", "", "| Education | Users |", "| --- | ---: |"])
    for value, count in summary_counts(rows, "education_level").items():
        lines.append(f"| {value} | {count} |")
    lines.extend(["", "### Marital Status", "", "| Marital status | Users |", "| --- | ---: |"])
    for value, count in summary_counts(rows, "marital_status").items():
        lines.append(f"| {value} | {count} |")
    lines.extend(["", "### Occupation Groups", "", "| Occupation group | Users |", "| --- | ---: |"])
    for value, count in summary_counts(rows, "occupation_group").items():
        lines.append(f"| {value} | {count} |")
    lines.extend(["", "### Geography", "", "| State | Users |", "| --- | ---: |"])
    for value, count in summary_counts(rows, "state").items():
        lines.append(f"| {value} | {count} |")
    lines.extend(
        [
            "",
            "## Selected Users",
            "",
            "| # | File | Age | Gender | Education | Occupation | State |",
            "| ---: | --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for index, row in enumerate(rows, start=1):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(index),
                    f"`{row['file']}`",
                    str(row.get("age") or ""),
                    str(row.get("gender") or ""),
                    str(row.get("education_level") or ""),
                    str(row.get("occupation") or ""),
                    str(row.get("state") or ""),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.curated_dir.exists():
        raise FileNotFoundError(f"Curated persona directory not found: {args.curated_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    candidates = load_candidates(args.curated_dir, args.max_candidates)
    selected = select_diverse(candidates, args.sample_size)
    fields = [
        "file",
        "path",
        "id",
        "record_index",
        "age",
        "age_band",
        "gender",
        "marital_status",
        "education_level",
        "occupation",
        "occupation_group",
        "city",
        "state",
        "country",
        "zipcode",
        "core",
        "professional",
        "hobbies",
        "skills",
    ]
    write_json(
        args.output_dir / "nemotron_survey_users_50.json",
        {
            "source": "Nemotron curated personas",
            "selection_method": "deterministic greedy diversity sample; no domain relevance filter",
            "candidate_count": len(candidates),
            "selected_count": len(selected),
            "variation_weights": VARIATION_WEIGHTS,
            "selected": selected,
        },
    )
    write_csv(args.output_dir / "nemotron_survey_users_50.csv", selected, fields)
    (args.output_dir / "nemotron_survey_user_ids_50.txt").write_text(
        "\n".join(row["file"] for row in selected) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "nemotron_survey_users_50.md").write_text(
        render_markdown(selected, len(candidates)),
        encoding="utf-8",
    )
    print(f"Wrote {len(selected)} survey users to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
