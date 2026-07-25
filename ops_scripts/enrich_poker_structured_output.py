"""Add persona.analysis context to poker structured_output.json.

The poker job already has 6 evaluation contexts from the task runner.
This script adds a persona.analysis context with cognitive/demographic traits
from the persona YAML files, enriching the aggregation for the PDF report.

Usage:
  python ops_scripts/enrich_poker_structured_output.py
"""

import json
import re
import yaml
from pathlib import Path

JOBS_DIR = Path(__file__).resolve().parent.parent / "jobs"
REPO_ROOT = JOBS_DIR.parent
JOB_NAME = "texas-holdem-1000-persona"

TRAIT_KEYS = [
    "risk_tolerance", "domain", "decision_style", "tech_savviness",
    "years_experience", "cog_abstraction", "dominant_trait",
    "emotional_state", "trust_level",
    "academic_field", "seniority", "cog_detail_orientation",
    "cog_big_picture_vs_detail", "cog_risk_framing",
    "cog_optimism", "cog_curiosity", "cog_skepticism",
    "cog_open_mindedness", "cog_assertiveness",
    "cog_empathy_expression", "cog_humor",
    "cog_confidence_calibration", "cog_numeracy_comfort",
    "cog_ambiguity_tolerance", "cog_perfectionism",
    "cog_procrastination", "cog_decision_speed",
    "cog_attention_span", "cog_learning_pace",
    "cog_big_picture_vs_detail", "cog_formality",
    "cog_directness", "cog_verbosity",
]


def load_persona_yaml(persona_meta: dict) -> dict:
    raw_path = persona_meta.get("persona_path", "")
    if not raw_path:
        return {}
    path = Path(raw_path)
    if not path.is_file():
        relative = raw_path.replace("\\", "/")
        if "persona/" in relative:
            rel_part = relative[relative.index("persona/"):]
            path = REPO_ROOT / rel_part
    if not path.is_file():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict):
            return data.get("dimensions") or data
    except Exception:
        pass
    return {}


def build_persona_context(persona_meta: dict) -> list[dict] | None:
    """Build a persona.analysis context from the persona YAML dimensions."""
    persona_dims = load_persona_yaml(persona_meta)
    if not persona_dims:
        return None

    trait_facets = []
    for key in TRAIT_KEYS:
        val = persona_dims.get(key)
        if val is not None and isinstance(val, str) and val.strip():
            trait_facets.append({
                "key": key,
                "label": key.replace("_", " ").title(),
                "role": "primary" if key in ("risk_tolerance", "domain", "decision_style") else "evidence",
                "kind": "categorical",
                "value": val.strip(),
            })

    # Numerical facets from persona
    years_exp = persona_dims.get("years_experience", "")
    if years_exp:
        match = re.search(r"(\d+)", str(years_exp))
        if match:
            trait_facets.append({
                "key": "years_experience_years",
                "label": "Years Experience (numeric)",
                "role": "evidence",
                "kind": "numerical",
                "value": float(match.group(1)),
            })

    if not trait_facets:
        return None

    return {
        "key": "persona.analysis",
        "label": "Persona analysis",
        "contextType": "persona_analysis",
        "facets": trait_facets,
    }


def main():
    job_dir = JOBS_DIR / JOB_NAME
    if not job_dir.is_dir():
        print(f"Job directory not found: {job_dir}")
        return

    enriched = 0
    skipped = 0
    errors = 0

    for trial_dir in sorted(job_dir.iterdir()):
        if not trial_dir.is_dir() or trial_dir.name.startswith("."):
            continue

        target_file = trial_dir / "verifier" / "structured_output.json"
        persona_meta_file = trial_dir / "persona_meta.json"

        if not target_file.is_file():
            skipped += 1
            continue
        if not persona_meta_file.is_file():
            skipped += 1
            continue

        try:
            persona_meta = json.loads(persona_meta_file.read_text(encoding="utf-8"))
        except Exception:
            errors += 1
            continue

        # Build persona context
        persona_ctx = build_persona_context(persona_meta)
        if persona_ctx is None:
            skipped += 1
            continue

        # Read existing structured_output
        try:
            payload = json.loads(target_file.read_text(encoding="utf-8"))
        except Exception:
            errors += 1
            continue

        # Check if persona.analysis already exists — skip if so
        existing_keys = [c.get("key") for c in payload.get("contexts", [])]
        if "persona.analysis" in existing_keys:
            skipped += 1
            continue

        # Add the persona context
        contexts = payload.get("contexts", [])
        contexts.append(persona_ctx)
        payload["contexts"] = contexts

        # Write back
        target_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  ENRICHED {trial_dir.name} — added persona.analysis ({len(persona_ctx['facets'])} facets)")
        enriched += 1

    print(f"\nDone. Enriched: {enriched}, Skipped: {skipped}, Errors: {errors}")

    if enriched > 0:
        agg_file = job_dir / "aggregation.json"
        if agg_file.is_file():
            agg_file.unlink()
            print(f"Deleted {JOB_NAME}/aggregation.json to force rebuild")


if __name__ == "__main__":
    main()
