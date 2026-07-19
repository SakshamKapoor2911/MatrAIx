#!/usr/bin/env python3
"""Sample personas and run high-confidence internal consistency checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from persona.synthesis.sampler import DEFAULT_GRAPH_PATH  # noqa: E402
from persona.synthesis.sampler import PersonaForwardSampler, SamplingConfig  # noqa: E402
from persona.synthesis.sampler.audit import consistency_audit, write_rules_csv  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--n", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("/tmp/persona_synthesis_consistency_audit"),
    )
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    sampler = PersonaForwardSampler(args.graph, SamplingConfig(seed=args.seed))
    idx = sampler.sample_indices(args.n)
    samples = [sampler.decode_row(idx, i) for i in range(args.n)]
    summary = consistency_audit(samples)
    (args.outdir / "consistency_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_rules_csv(summary, args.outdir / "consistency_rules.csv")
    print(
        json.dumps(
            {
                key: summary[key]
                for key in [
                    "n",
                    "any_hard",
                    "any_hard_share",
                    "any_hard_or_strong",
                    "any_hard_or_strong_share",
                    "any_flagged",
                    "any_flagged_share",
                ]
            },
            indent=2,
        )
    )
    if summary["any_hard"] > 0:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
