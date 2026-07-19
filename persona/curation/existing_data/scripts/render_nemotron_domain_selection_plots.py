#!/usr/bin/env python3
"""Render Nemotron domain-selection plots from committed selection artifacts.

The PR90 figures are report artifacts; this script is the reproducible path for
regenerating them. It only needs the standard library for SVG outputs. If
Matplotlib is installed, it also writes PNG/PDF/SVG variants of the
within-domain cluster figure.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


DEFAULT_INPUT_DIR = Path(
    "persona/curation/existing_data/samples/nemotron_domain_selection"
)
DEFAULT_OUTPUT_DIR = Path(
    "persona/curation/existing_data/outputs/nemotron_domain_selection"
)
DOMAIN_LABELS = {
    "movie": "Movie / film",
    "beauty": "Beauty",
    "game": "Games",
    "finance": "Finance",
    "medical": "Medical",
    "ecommerce": "E-commerce",
}
DOMAIN_COLORS = {
    "Movie / film": "#4E79A7",
    "Beauty": "#E15759",
    "Games": "#59A14F",
    "Finance": "#F28E2B",
    "Medical": "#B07AA1",
    "E-commerce": "#76B7B2",
}


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--matplotlib",
        action="store_true",
        help="Also render Matplotlib PNG/PDF/SVG outputs if matplotlib is installed.",
    )
    return parser.parse_args(argv)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def stable_unit(*parts: Any) -> float:
    raw = "::".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def svg_document(width: int, height: int, body: list[str]) -> str:
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img">',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
            *body,
            "</svg>",
            "",
        ]
    )


def svg_text(
    x: float,
    y: float,
    text: str,
    *,
    size: int = 12,
    weight: str = "400",
    anchor: str = "start",
    fill: str = "#222222",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
        f'fill="{fill}">{html.escape(text)}</text>'
    )


def domain_rows(selection: dict[str, Any]) -> list[dict[str, Any]]:
    selected = selection.get("selected") or {}
    candidate_counts = selection.get("candidate_counts") or {}
    rows = []
    for domain_key, users in selected.items():
        domain = DOMAIN_LABELS.get(domain_key, domain_key)
        ages = [safe_float(user.get("age")) for user in users if str(user.get("age", "")).strip()]
        occupations = {str(user.get("occupation") or "") for user in users if user.get("occupation")}
        genders = Counter(str(user.get("gender") or "Unknown") for user in users)
        rows.append(
            {
                "domain": domain,
                "domain_key": domain_key,
                "candidate_count": candidate_counts.get(domain_key, ""),
                "selected_count": len(users),
                "mean_age": round(sum(ages) / len(ages), 3) if ages else "",
                "unique_occupations": len(occupations),
                "female_count": genders.get("Female", 0),
                "male_count": genders.get("Male", 0),
                "unknown_gender_count": sum(
                    count for gender, count in genders.items() if gender not in {"Female", "Male"}
                ),
            }
        )
    return rows


def write_metrics(selection: dict[str, Any], output_dir: Path) -> None:
    rows = domain_rows(selection)
    write_csv(
        output_dir / "nemotron_overall_diversity_metrics.csv",
        rows,
        [
            "domain",
            "domain_key",
            "candidate_count",
            "selected_count",
            "mean_age",
            "unique_occupations",
            "female_count",
            "male_count",
            "unknown_gender_count",
        ],
    )
    write_csv(
        output_dir / "nemotron_within_domain_diversity_metrics.csv",
        rows,
        [
            "domain",
            "selected_count",
            "mean_age",
            "unique_occupations",
            "female_count",
            "male_count",
            "unknown_gender_count",
        ],
    )


def render_overall_projection_from_rows(rows: list[dict[str, Any]], output_dir: Path) -> None:
    width, height = 980, 500
    left, right, top, bottom = 95, 40, 70, 90
    max_candidates = max(
        int(float(row.get("candidate_count") or row.get("users") or 0)) for row in rows
    ) or 1
    body = [
        svg_text(30, 36, "Nemotron domain candidate pool and selected users", size=22, weight="700"),
        svg_text(30, 58, "Bubble size encodes selected users; x-axis encodes candidate pool size when available.", size=12, fill="#555"),
    ]
    plot_w = width - left - right
    plot_h = height - top - bottom
    for i in range(6):
        x = left + plot_w * i / 5
        value = max_candidates * i / 5
        body.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + plot_h}" stroke="#e6e6e6"/>')
        body.append(svg_text(x, top + plot_h + 24, f"{value/1000:.0f}k", size=11, anchor="middle", fill="#666"))
    for index, row in enumerate(rows):
        y = top + 25 + index * (plot_h - 20) / max(1, len(rows) - 1)
        candidate_count = int(float(row.get("candidate_count") or row.get("users") or 0))
        selected_count = int(float(row.get("selected_count") or row.get("users") or 0))
        x = left + (candidate_count / max_candidates) * plot_w
        color = DOMAIN_COLORS.get(row["domain"], "#888888")
        radius = 8 + math.sqrt(selected_count) * 2.4
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#f2f2f2"/>')
        body.append(svg_text(26, y + 4, str(row["domain"]), size=12, weight="700"))
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{color}" fill-opacity="0.82" stroke="#333"/>')
        if row.get("candidate_count") not in (None, ""):
            label = f"{candidate_count:,} candidates; {selected_count} selected"
        else:
            label = f"{selected_count} selected users"
        body.append(svg_text(x + radius + 8, y + 4, label, size=11, fill="#333"))
    body.append(svg_text(left + plot_w / 2, height - 24, "Candidate users matching domain keywords", size=12, anchor="middle"))
    (output_dir / "nemotron_overall_diversity_projection.svg").write_text(
        svg_document(width, height, body),
        encoding="utf-8",
    )


def render_overall_projection(selection: dict[str, Any], output_dir: Path) -> None:
    render_overall_projection_from_rows(domain_rows(selection), output_dir)


def user_records(selection: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for domain_key, users in (selection.get("selected") or {}).items():
        domain = DOMAIN_LABELS.get(domain_key, domain_key)
        for user in users:
            record = dict(user)
            record["domain"] = domain
            record["domain_key"] = domain_key
            records.append(record)
    return records


def render_within_domain_projection_from_records(records: list[dict[str, Any]], output_dir: Path) -> None:
    domains = []
    for record in records:
        if record["domain"] not in domains:
            domains.append(record["domain"])
    width, height = 1040, 620
    left, right, top, bottom = 80, 40, 70, 110
    plot_w = width - left - right
    plot_h = height - top - bottom
    ages = [safe_float(row.get("age")) for row in records if str(row.get("age", "")).strip()]
    min_age, max_age = (min(ages), max(ages)) if ages else (18.0, 80.0)
    domain_x = {
        domain: left + (index + 0.5) * plot_w / max(1, len(domains))
        for index, domain in enumerate(domains)
    }
    body = [
        svg_text(30, 36, "Nemotron selected users by domain", size=22, weight="700"),
        svg_text(30, 58, "Each point is one selected persona; y-axis is age and horizontal jitter separates users.", size=12, fill="#555"),
    ]
    for i in range(6):
        value = min_age + (max_age - min_age) * i / 5
        y = top + plot_h - (value - min_age) / max(1, max_age - min_age) * plot_h
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#e8e8e8"/>')
        body.append(svg_text(left - 12, y + 4, f"{value:.0f}", size=11, anchor="end", fill="#666"))
    for domain in domains:
        x = domain_x[domain]
        body.append(svg_text(x, height - 58, domain, size=12, anchor="middle", weight="700"))
    for row in records:
        age = safe_float(row.get("age"), min_age)
        domain = row["domain"]
        jitter = (stable_unit(row.get("file"), row.get("occupation")) - 0.5) * (plot_w / max(1, len(domains))) * 0.62
        x = domain_x[domain] + jitter
        y = top + plot_h - (age - min_age) / max(1, max_age - min_age) * plot_h
        color = DOMAIN_COLORS.get(domain, "#888888")
        title = html.escape(f"{row.get('file')} | {row.get('occupation')} | age {row.get('age')}")
        body.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.8" fill="{color}" fill-opacity="0.75" '
            f'stroke="#ffffff" stroke-width="0.7"><title>{title}</title></circle>'
        )
    body.append(svg_text(22, top + plot_h / 2, "Age", size=12, anchor="middle"))
    (output_dir / "nemotron_within_domain_diversity_projection.svg").write_text(
        svg_document(width, height, body),
        encoding="utf-8",
    )


def render_within_domain_projection(selection: dict[str, Any], output_dir: Path) -> None:
    render_within_domain_projection_from_records(user_records(selection), output_dir)


def user_records_from_cluster_rows(user_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [dict(row) for row in user_rows]


def render_cluster_projection(user_rows: list[dict[str, str]], output_dir: Path) -> None:
    if not user_rows:
        return
    domains = []
    for row in user_rows:
        if row["domain"] not in domains:
            domains.append(row["domain"])
    width, height = 1120, 680
    left, right, top, bottom = 90, 40, 72, 130
    plot_w = width - left - right
    plot_h = height - top - bottom
    domain_x = {
        domain: left + (index + 0.5) * plot_w / max(1, len(domains))
        for index, domain in enumerate(domains)
    }
    cluster_values = sorted({int(row["cluster"]) for row in user_rows if row.get("cluster")}, reverse=True)
    max_cluster = max(cluster_values) if cluster_values else 1
    body = [
        svg_text(30, 38, "Nemotron within-domain user clusters", size=22, weight="700"),
        svg_text(30, 60, "Each point is one selected persona, grouped by domain and colored by domain.", size=12, fill="#555"),
    ]
    for cluster in range(1, max_cluster + 1):
        y = top + plot_h - (cluster - 1) / max(1, max_cluster - 1) * plot_h
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#e8e8e8"/>')
        body.append(svg_text(left - 12, y + 4, f"C{cluster}", size=11, anchor="end", fill="#666"))
    for domain in domains:
        x = domain_x[domain]
        body.append(svg_text(x, height - 74, domain, size=12, anchor="middle", weight="700"))
    for row in user_rows:
        domain = row["domain"]
        cluster = int(row.get("cluster") or 1)
        x = domain_x[domain] + (stable_unit(row.get("file"), row.get("cluster")) - 0.5) * (plot_w / max(1, len(domains))) * 0.68
        y = top + plot_h - (cluster - 1) / max(1, max_cluster - 1) * plot_h
        y += (stable_unit(row.get("occupation"), row.get("file")) - 0.5) * 26
        color = DOMAIN_COLORS.get(domain, "#888888")
        title = html.escape(f"{row.get('file')} | cluster {cluster} | {row.get('occupation')}")
        body.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.0" fill="{color}" fill-opacity="0.78" '
            f'stroke="#ffffff" stroke-width="0.7"><title>{title}</title></circle>'
        )
    body.append(svg_text(22, top + plot_h / 2, "Cluster", size=12, anchor="middle"))
    (output_dir / "nemotron_within_domain_cluster_projection.svg").write_text(
        svg_document(width, height, body),
        encoding="utf-8",
    )


def render_cluster_matplotlib(user_rows: list[dict[str, str]], output_dir: Path) -> None:
    if not user_rows:
        return
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "Matplotlib is required for --matplotlib outputs. Install matplotlib or omit --matplotlib."
        ) from exc

    domains = []
    for row in user_rows:
        if row["domain"] not in domains:
            domains.append(row["domain"])
    domain_index = {domain: index for index, domain in enumerate(domains)}
    fig, ax = plt.subplots(figsize=(13, 7.5))
    for domain in domains:
        rows = [row for row in user_rows if row["domain"] == domain]
        xs = [
            domain_index[domain] + (stable_unit(row.get("file"), row.get("cluster")) - 0.5) * 0.56
            for row in rows
        ]
        ys = [
            int(row.get("cluster") or 1)
            + (stable_unit(row.get("occupation"), row.get("file")) - 0.5) * 0.18
            for row in rows
        ]
        ax.scatter(
            xs,
            ys,
            s=54,
            alpha=0.78,
            label=domain,
            color=DOMAIN_COLORS.get(domain, "#888888"),
            edgecolor="white",
            linewidth=0.7,
        )
    ax.set_title("Nemotron within-domain user clusters")
    ax.set_ylabel("Cluster")
    ax.set_xticks(range(len(domains)))
    ax.set_xticklabels(domains, rotation=20, ha="right")
    ax.grid(axis="y", alpha=0.24)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False)
    fig.tight_layout()
    for suffix in ("png", "pdf", "svg"):
        fig.savefig(
            output_dir / f"nemotron_within_domain_cluster_projection_matplotlib.{suffix}",
            dpi=220 if suffix == "png" else None,
        )
    plt.close(fig)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    input_dir = args.input_dir
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    user_cluster_rows = read_csv(input_dir / "nemotron_within_domain_user_clusters_matplotlib.csv")
    if not user_cluster_rows:
        user_cluster_rows = read_csv(input_dir / "nemotron_within_domain_user_clusters.csv")
    if not user_cluster_rows:
        raise FileNotFoundError(
            "Missing cluster CSV: expected nemotron_within_domain_user_clusters.csv "
            "or nemotron_within_domain_user_clusters_matplotlib.csv"
        )

    selection_path = input_dir / "nemotron_test_users_50_per_domain.json"
    if selection_path.exists():
        selection = read_json(selection_path)
        write_metrics(selection, output_dir)
        render_overall_projection(selection, output_dir)
        render_within_domain_projection(selection, output_dir)
    else:
        overall_metrics = read_csv(input_dir / "nemotron_overall_diversity_metrics.csv")
        within_metrics = read_csv(input_dir / "nemotron_within_domain_diversity_metrics.csv")
        if not overall_metrics:
            overall_metrics = [
                {"domain": domain, "users": count}
                for domain, count in Counter(row["domain"] for row in user_cluster_rows).items()
            ]
        if not within_metrics:
            within_metrics = overall_metrics
        render_overall_projection_from_rows(overall_metrics, output_dir)
        render_within_domain_projection_from_records(
            user_records_from_cluster_rows(user_cluster_rows),
            output_dir,
        )
        if overall_metrics:
            write_csv(output_dir / "nemotron_overall_diversity_metrics.csv", overall_metrics, list(overall_metrics[0]))
        if within_metrics:
            write_csv(
                output_dir / "nemotron_within_domain_diversity_metrics.csv",
                within_metrics,
                list(within_metrics[0]),
            )
    render_cluster_projection(user_cluster_rows, output_dir)
    if args.matplotlib:
        render_cluster_matplotlib(user_cluster_rows, output_dir)

    print(f"Wrote Nemotron domain-selection plots to {output_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        raise SystemExit(f"ERROR: {exc}") from None
