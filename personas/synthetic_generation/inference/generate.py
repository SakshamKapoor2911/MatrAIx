"""Draft CLI for Task 2.2 persona generation.

Flow:
    skeleton (assigned dimension values)
      -> render prompt (base + domain overlay)
      -> LLM (provider-agnostic client)
      -> parse JSON persona (dimensions + narrative + provenance)
      -> validate (TODO: add a formal persona JSON Schema)
      -> write to outputs/

STATUS: structural draft. The two stubs below are the parts that depend on the
OPEN methodology decision (see README "Open decision"):
  - build_skeleton(): how the dimension values get assigned (heuristic / LLM / hybrid)
  - parsing/validation hardening
Everything else (prompt rendering, model call, IO) is wired.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import uuid
from pathlib import Path

import yaml

from client import LLMClient  # run as: python inference/generate.py ...

BASE_DIR = Path(__file__).resolve().parents[1]
PROMPTS_DIR = BASE_DIR / "prompts"
OUTPUTS_DIR = BASE_DIR / "outputs"


def build_skeleton(domain: str, seed: dict | None = None) -> dict:
    """Produce the structured dimension assignment for one persona.

    OPEN DECISION (README): this is the 'heuristic combination' step. v0 placeholder
    returns only the seed anchors and lets the LLM fill the rest coherently
    (LLM-heavy). Swap in:
      - heuristic sampling from real priors (ACS PUMS / curated marginals), or
      - the Task 1 ACS skeleton provider,
    behind this same function signature.
    """
    skeleton = {"domain": domain}
    if seed:
        skeleton.update(seed)
    # TODO: assign dimension values per the chosen strategy.
    return skeleton


def _load_prompt(path: Path) -> str:
    """Read a prompt YAML and return its `content` field."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("content", "")


def render_prompt(domain: str, skeleton: dict) -> tuple[str, str]:
    """Return (system, user) by composing base prompt + domain overlay + skeleton."""
    system = _load_prompt(PROMPTS_DIR / "base_persona.yaml")
    overlay_path = PROMPTS_DIR / "domains" / f"{domain}.yaml"
    overlay = _load_prompt(overlay_path) if overlay_path.exists() else ""
    user = (
        f"{overlay}\n\n"
        f"## Skeleton (assigned dimension values)\n"
        f"```json\n{json.dumps(skeleton, ensure_ascii=False, indent=2)}\n```\n"
        f"Return ONE persona as JSON conforming to the output contract in the base prompt."
    )
    return system, user


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", required=True, help="Target domain, e.g. finance")
    parser.add_argument("--model", required=True, help="Registry model name, e.g. gpt-4o")
    parser.add_argument("--n", type=int, default=1, help="How many personas to generate")
    parser.add_argument("--config", default=None, help="Path to model registry YAML")
    args = parser.parse_args(argv)

    client = LLMClient(args.config)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    for _ in range(args.n):
        skeleton = build_skeleton(args.domain)
        system, user = render_prompt(args.domain, skeleton)
        raw = client.generate(args.model, system, user)
        # TODO: robust JSON extraction + schema validation (schema TBD) + dimension-value checks.
        pid = f"mx_synth_{uuid.uuid4().hex[:12]}"
        out_path = OUTPUTS_DIR / f"{pid}.json"
        record = {
            "persona_id": pid,
            "domain": args.domain,
            "_raw_model_output": raw,
            "provenance": {
                "model": args.model,
                "prompt_version": f"base_persona@v0.1+{args.domain}@v0.1",
                "skeleton_source": "seed_sample@v0",
                "created": dt.datetime.now(dt.timezone.utc).isoformat(),
            },
        }
        out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[generate] wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
