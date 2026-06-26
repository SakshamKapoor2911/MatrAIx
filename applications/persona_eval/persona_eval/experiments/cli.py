from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import List, Sequence

from persona_eval.experiments.applications import (
    list_application_specs,
    parse_application_ref,
)
from persona_eval.experiments.batch import ExperimentBatchRunner, build_run_specs
from persona_eval.experiments.suite import ExperimentApplicationRunner
from persona_eval.persona import get_persona, load_personas
from persona_eval.types import DEFAULT_PERSONA_MODEL, Persona


def default_output_root() -> Path:
    repo_root = Path(__file__).resolve().parents[4]
    return repo_root / "data" / "cache" / "persona_eval" / "paper_experiments"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m persona_eval.experiments",
        description="Run headless PersonaEval paper experiments without Harbor.",
    )
    parser.add_argument(
        "--list-applications",
        action="store_true",
        help="Print available application targets and exit.",
    )
    parser.add_argument(
        "--application",
        action="append",
        default=[],
        help=(
            "Application target. Examples: movie, recai:game, finance, medical. "
            "Repeat for a cross product with selected personas."
        ),
    )
    parser.add_argument(
        "--all-applications",
        action="store_true",
        help="Run all registered chatbot application targets.",
    )
    parser.add_argument("--persona", action="append", default=[])
    parser.add_argument("--persona-query", default="")
    parser.add_argument("--num-personas", type=int, default=1)
    parser.add_argument("--max-runs", type=int, default=None)
    parser.add_argument("--parallel", type=int, default=10)
    parser.add_argument("--max-turns", type=int, default=3)
    parser.add_argument("--min-turns", type=int, default=3)
    parser.add_argument("--goal-context", default="scenario_default")
    parser.add_argument(
        "--api-url",
        default=os.environ.get("MATRIX_CHATBOT_API_URL", "http://127.0.0.1:8000"),
    )
    parser.add_argument(
        "--persona-model",
        default=os.environ.get("MATRIX_EXPERIMENT_PERSONA_MODEL", DEFAULT_PERSONA_MODEL),
    )
    parser.add_argument("--retries", type=int, default=6)
    parser.add_argument("--retry-delay", type=float, default=2.0)
    parser.add_argument("--out", default=None)
    parser.add_argument("--batch-id", default=None)
    return parser


def run_from_args(argv: Sequence[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv))
    if args.list_applications:
        print(
            json.dumps(
                [app.to_dict() for app in list_application_specs()],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    applications = _select_applications(args.application, args.all_applications)
    personas = _select_personas(
        persona_ids=args.persona,
        query=args.persona_query,
        limit=args.num_personas,
    )
    if not applications:
        parser.error("select at least one --application or use --all-applications")
    if not personas:
        parser.error("select at least one persona")

    specs = build_run_specs(
        personas=personas,
        applications=applications,
        api_url=args.api_url,
        persona_model=args.persona_model,
        max_turns=args.max_turns,
        min_turns=args.min_turns,
        goal_context_id=args.goal_context,
        retries=args.retries,
        retry_delay=args.retry_delay,
        max_runs=args.max_runs,
    )
    batch_id = args.batch_id or "batch_{}".format(uuid.uuid4().hex[:12])
    output_dir = Path(args.out) if args.out else default_output_root() / batch_id
    runner = ExperimentApplicationRunner()
    batch = ExperimentBatchRunner(
        applications=applications,
        personas=personas,
        run_one=runner.run,
    )
    summary = batch.run_batch(
        specs,
        output_dir=output_dir,
        max_workers=args.parallel,
    )
    print(
        json.dumps(
            {
                "outputDir": str(output_dir),
                "total": summary["total"],
                "statusCounts": summary["statusCounts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if summary.get("statusCounts", {}).get("error", 0) == 0 else 1


def _select_applications(refs: Sequence[str], all_applications: bool):
    if all_applications:
        return list_application_specs()
    selected = []
    seen = set()
    for ref in refs:
        app = parse_application_ref(ref)
        if app.key not in seen:
            selected.append(app)
            seen.add(app.key)
    return selected


def _select_personas(
    *,
    persona_ids: Sequence[str],
    query: str,
    limit: int,
) -> List[Persona]:
    if persona_ids:
        return [get_persona(persona_id) for persona_id in persona_ids]
    return load_personas(query=query, limit=limit)


def main() -> int:
    return run_from_args(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
