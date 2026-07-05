"""Package entry point for ``python -m persona_eval``."""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "persona-eval no longer provides a standalone in-process CLI.\n"
        "Launch evaluations through Harbor instead:\n"
        "  uv run python application/scripts/generate_application_job.py --task <task> --execution-mode auto\n"
        "  uv run harbor run -c configs/jobs/application-task-job-recipe/<job>.yaml\n"
        "Or use the PersonaEval Cockpit (POST /api/harbor/jobs).",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
