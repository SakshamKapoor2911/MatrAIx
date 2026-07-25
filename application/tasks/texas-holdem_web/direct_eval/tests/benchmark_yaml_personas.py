"""End-to-end benchmark running DirectEngineEvaluator across real persona YAML files."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

# Ensure matraix_repo and task roots are on sys.path
_TASK_DIR = Path(__file__).resolve().parents[2]
if str(_TASK_DIR) not in sys.path:
    sys.path.insert(0, str(_TASK_DIR))

_REPO_ROOT = Path(__file__).resolve().parents[5]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from direct_eval.evaluator import DirectEngineEvaluator





def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark Direct Engine on real persona YAML files.")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of personas to run (0 for all)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for trials")
    args = parser.parse_args()

    yaml_dir = _REPO_ROOT / "persona" / "datasets" / "bench-dev-sample"
    if not yaml_dir.exists():
        yaml_dir = _REPO_ROOT / "worktrees" / "staging-synthetic-tasks" / "persona" / "datasets" / "bench-dev-sample"

    if not yaml_dir.exists():
        print(f"Error: YAML directory not found at {yaml_dir}", file=sys.stderr)
        return 1


    yaml_files = sorted(yaml_dir.glob("persona_*.yaml"))
    if args.limit > 0:
        yaml_files = yaml_files[: args.limit]

    print(f"Running DirectEngineEvaluator on {len(yaml_files)} persona YAML files (seed={args.seed})...\n")

    results = []
    win_count = 0
    risk_postures = {}
    exploration_styles = {}
    task_strategies = {}

    for idx, fpath in enumerate(yaml_files, start=1):
        data = yaml.safe_load(fpath.read_text(encoding="utf-8"))
        persona_id = data.get("persona_id", fpath.stem)
        dims = data.get("dimensions", {})

        evaluator = DirectEngineEvaluator(persona_dimensions=dims, seed=args.seed)
        res = evaluator.run()

        results.append((persona_id, res))
        if res.get("chip_delta", 0) > 0:
            win_count += 1

        rp = res.get("risk_posture", "unknown")
        es = res.get("exploration_style", "unknown")
        ts = res.get("task_strategy_basis", "unknown")

        risk_postures[rp] = risk_postures.get(rp, 0) + 1
        exploration_styles[es] = exploration_styles.get(es, 0) + 1
        task_strategies[ts] = task_strategies.get(ts, 0) + 1

    print(f"--- Benchmark Summary ({len(results)} personas evaluated) ---")
    print(f"Win Rate: {win_count}/{len(results)} ({win_count / len(results):.1%})")
    print(f"Risk Posture Distribution: {dict(risk_postures)}")
    print(f"Exploration Style Distribution: {dict(exploration_styles)}")
    print(f"Task Strategy Basis Distribution: {dict(task_strategies)}")
    print("--- End Benchmark ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
