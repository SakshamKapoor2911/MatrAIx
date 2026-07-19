#!/usr/bin/env python3
"""Generate a reproducible quality report for the Persona Full DAG."""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from persona.synthesis.sampler import DEFAULT_GRAPH_PATH, graph_summary  # noqa: E402
from persona.synthesis.sampler import PersonaForwardSampler, SamplingConfig  # noqa: E402
from persona.synthesis.sampler.audit import consistency_audit, marginal_audit  # noqa: E402
from persona.synthesis.sampler.validation import validate_graph  # noqa: E402

DEFAULT_FOCUS_NODES = [
    "region",
    "age_bracket",
    "gender_identity",
    "urbanicity",
    "socioeconomic_band",
    "highest_education",
    "primary_language",
    "english_proficiency",
    "demo_ethnicity_broad",
    "demo_religion_affiliation",
    "demo_employment_status",
    "demo_children_count",
    "life_stage",
    "years_experience",
    "seniority",
    "role_function",
    "domain",
    "tech_savviness",
]


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _seconds(value: float) -> str:
    return f"{value:.4f}s"


def _pct(value: float) -> str:
    return f"{100 * value:.2f}%"


def _top_values(row: dict[str, Any], *, limit: int = 4) -> str:
    empirical = row["empirical"]
    prior = row["prior"]
    top = sorted(empirical.items(), key=lambda item: item[1], reverse=True)[:limit]
    return "; ".join(
        f"{value}: sample {_pct(emp)}, prior {_pct(prior.get(value, 0.0))}"
        for value, emp in top
    )


def build_report(
    *,
    graph_path: Path,
    n: int,
    seed: int,
    top_marginals: int,
) -> dict[str, Any]:
    timings: dict[str, float] = {}
    total_start = time.perf_counter()

    start = time.perf_counter()
    sampler = PersonaForwardSampler(graph_path, SamplingConfig(seed=seed))
    timings["load_and_compile_seconds"] = time.perf_counter() - start

    start = time.perf_counter()
    validation = validate_graph(sampler.graph)
    timings["static_validation_seconds"] = time.perf_counter() - start

    start = time.perf_counter()
    idx = sampler.sample_indices(n)
    timings["sample_indices_seconds"] = time.perf_counter() - start

    start = time.perf_counter()
    marginals = marginal_audit(sampler, idx, DEFAULT_FOCUS_NODES)
    timings["marginal_audit_seconds"] = time.perf_counter() - start

    start = time.perf_counter()
    consistency = consistency_audit(sampler.decode_row(idx, i) for i in range(n))
    timings["consistency_audit_seconds"] = time.perf_counter() - start

    timings["total_seconds"] = time.perf_counter() - total_start
    timings["sampling_throughput_per_second"] = (
        n / timings["sample_indices_seconds"]
        if timings["sample_indices_seconds"] > 0
        else 0.0
    )
    timings["end_to_end_throughput_per_second"] = (
        n / timings["total_seconds"] if timings["total_seconds"] > 0 else 0.0
    )

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "graph": _display_path(graph_path),
        "sample_count": n,
        "seed": seed,
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "graph_summary": graph_summary(sampler.graph),
        "validation": validation,
        "timings": timings,
        "focus_node_marginals": [
            {
                "node": row["node"],
                "tvd_vs_prior": row["tvd_vs_prior"],
                "top_sample_values": _top_values(row),
            }
            for row in marginals
        ],
        "top_focus_node_marginals": [
            {
                "node": row["node"],
                "tvd_vs_prior": row["tvd_vs_prior"],
                "top_sample_values": _top_values(row),
            }
            for row in marginals[:top_marginals]
        ],
        "consistency": {
            key: consistency[key]
            for key in [
                "n",
                "any_hard",
                "any_hard_share",
                "any_hard_or_strong",
                "any_hard_or_strong_share",
                "any_flagged",
                "any_flagged_share",
                "severity_issue_counts",
                "group_issue_counts",
                "rules",
            ]
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    graph = report["graph_summary"]
    validation = report["validation"]
    timings = report["timings"]
    consistency = report["consistency"]
    lines = [
        "# Persona Full DAG Quality Report",
        "",
        "## Run",
        "",
        f"- Graph: `{report['graph']}`",
        f"- Samples: {report['sample_count']:,}",
        f"- Seed: {report['seed']}",
        f"- Generated at: {report['generated_at']}",
        f"- Python: {report['runtime']['python']}",
        f"- Platform: {report['runtime']['platform']}",
        "",
        "## Timing",
        "",
        "| Step | Time |",
        "| --- | ---: |",
        f"| Load and compile sampler | {_seconds(timings['load_and_compile_seconds'])} |",
        f"| Static validation | {_seconds(timings['static_validation_seconds'])} |",
        f"| Sample integer-coded DAG rows | {_seconds(timings['sample_indices_seconds'])} |",
        f"| Marginal audit | {_seconds(timings['marginal_audit_seconds'])} |",
        f"| Consistency audit | {_seconds(timings['consistency_audit_seconds'])} |",
        f"| End-to-end report runtime | {_seconds(timings['total_seconds'])} |",
        "",
        f"Sampling throughput: {timings['sampling_throughput_per_second']:.1f} samples/sec.",
        f"End-to-end throughput: {timings['end_to_end_throughput_per_second']:.1f} samples/sec.",
        "",
        "## Static Graph Validation",
        "",
        f"- Validation passed: `{str(validation['validation_passed']).lower()}`",
        f"- Nodes: {graph['nodes']:,}",
        f"- Emitted nodes: {graph['emitted_nodes']:,}",
        f"- Directed proposal edges: {graph['directed_edges']:,}",
        f"- Full CPT overlays: {graph['full_cpts']:,}",
        f"- Full CPT rows: {graph['full_cpt_rows']:,}",
        f"- Conditional masks: {graph['conditional_masks']:,}",
        f"- Missing refs: {len(validation['missing_refs'])}",
        f"- Duplicate node ids: {validation['duplicate_node_ids']}",
        f"- Duplicate directed pairs: {validation['duplicate_directed_pairs']}",
        f"- Cycle-free: `{str(validation['cycle_free']).lower()}`",
        f"- Topological dependency violations: {validation['topological_dependency_violations']}",
        "",
        "## Consistency Audit",
        "",
        f"- Personas with hard issues: {consistency['any_hard']:,} ({_pct(consistency['any_hard_share'])})",
        f"- Personas with hard or strong issues: {consistency['any_hard_or_strong']:,} ({_pct(consistency['any_hard_or_strong_share'])})",
        f"- Personas with any flagged issue: {consistency['any_flagged']:,} ({_pct(consistency['any_flagged_share'])})",
        f"- Severity issue counts: `{json.dumps(consistency['severity_issue_counts'], sort_keys=True)}`",
        f"- Group issue counts: `{json.dumps(consistency['group_issue_counts'], sort_keys=True)}`",
        "",
        "Top consistency rules:",
        "",
        "| Rule | Severity | Group | Count | Share |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for row in consistency["rules"][:20]:
        lines.append(
            f"| `{row['rule']}` | {row['severity']} | {row['group']} | "
            f"{row['count']:,} | {_pct(row['share'])} |"
        )
    if not consistency["rules"]:
        lines.append("| No flagged rules | - | - | 0 | 0.00% |")

    lines.extend([
        "",
        "## Focus-Node Marginal Drift",
        "",
        "TVD is total variation distance between the sample marginal and the node prior.",
        "",
        "| Node | TVD vs prior | Top sampled values |",
        "| --- | ---: | --- |",
    ])
    for row in report["focus_node_marginals"]:
        lines.append(
            f"| `{row['node']}` | {row['tvd_vs_prior']:.4f} | "
            f"{row['top_sample_values']} |"
        )

    lines.extend([
        "",
        "## Interpretation",
        "",
        "- The static graph checks are structural checks over the committed JSON.",
        "- The sampling audit is stochastic and should be compared with the seed and sample count.",
        "- Marginal drift from priors is expected for non-root nodes because pairwise edges, full CPTs, and masks intentionally condition later fields on earlier fields.",
        "- Hard consistency issues should be treated as blockers. Strong and soft issues are triage signals for graph refinement.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--n", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "persona" / "synthesis" / "reports" / "full_dag_quality_10000.md",
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--top-marginals", type=int, default=10)
    args = parser.parse_args()

    json_out = args.json_out or args.out.with_suffix(".json")
    report = build_report(
        graph_path=args.graph,
        n=args.n,
        seed=args.seed,
        top_marginals=args.top_marginals,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_markdown(report), encoding="utf-8")
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        json.dumps(
            {
                "report": str(args.out),
                "json": str(json_out),
                "sample_count": report["sample_count"],
                "sample_indices_seconds": report["timings"]["sample_indices_seconds"],
                "total_seconds": report["timings"]["total_seconds"],
                "validation_passed": report["validation"]["validation_passed"],
                "hard_issue_personas": report["consistency"]["any_hard"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
