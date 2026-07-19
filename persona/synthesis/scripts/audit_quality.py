#!/usr/bin/env python3
"""Sample personas and compare focus-node marginals with graph priors."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from persona.synthesis.sampler import DEFAULT_GRAPH_PATH  # noqa: E402
from persona.synthesis.sampler import PersonaForwardSampler, SamplingConfig  # noqa: E402
from persona.synthesis.sampler.audit import marginal_audit  # noqa: E402

DEFAULT_FOCUS = [
    "region",
    "age_bracket",
    "gender_identity",
    "urbanicity",
    "socioeconomic_band",
    "highest_education",
    "tech_savviness",
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
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--n", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("/tmp/persona_synthesis_quality_audit"),
    )
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    sampler = PersonaForwardSampler(args.graph, SamplingConfig(seed=args.seed))
    idx = sampler.sample_indices(args.n)
    rows = marginal_audit(sampler, idx, DEFAULT_FOCUS)
    summary = {
        "n": args.n,
        "focus_nodes": [
            {"node": row["node"], "tvd_vs_prior": row["tvd_vs_prior"]}
            for row in rows
        ],
    }
    (args.outdir / "quality_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    with (args.outdir / "focus_node_tvd.csv").open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.DictWriter(f, fieldnames=["node", "tvd_vs_prior"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {"node": row["node"], "tvd_vs_prior": row["tvd_vs_prior"]}
            )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
