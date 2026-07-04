"""Package entry point so ``python -m persona_eval ...`` runs the CLI."""

from __future__ import annotations

from persona_eval.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
