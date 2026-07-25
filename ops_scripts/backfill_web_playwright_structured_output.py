"""Enriched structured_output backfill for web-playwright tasks.

Generates 4 contexts with 15+ facets per trial:
  1. task_outcome.primary — basic pass/fail + reward
  2. decision.primary — choice metadata + task-specific fields
  3. persona.analysis — demographic + cognitive traits from YAML
  4. execution.quality — reasoning detail + quality signals

Usage:
  python ops_scripts/backfill_web_playwright_structured_output.py
"""

import json
import re
import yaml
from pathlib import Path

JOBS_DIR = Path(__file__).resolve().parent.parent / "jobs"
REPO_ROOT = JOBS_DIR.parent
JOB_PREFIX = "pg-web-playwright-"
TRIAL_EVAL_FILENAME = "structured_output.json"
TRAIT_KEYS = [
    "risk_tolerance", "domain", "decision_style", "tech_savviness",
    "years_experience", "cog_abstraction", "dominant_trait",
    "emotional_state", "trust_level", "cognitive_style",
    "academic_field", "seniority", "cog_detail_orientation",
    "cog_big_picture_vs_detail", "cog_risk_framing",
]


def load_persona_yaml(persona_meta: dict) -> dict:
    """Load persona YAML from the path in persona_meta.json."""
    raw_path = persona_meta.get("persona_path", "")
    if not raw_path:
        return {}
    # Handle absolute Windows path
    path = Path(raw_path)
    if not path.is_file():
        # Try relative to repo root
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


def extract_artifact_fields(trial_dir: Path) -> dict:
    """Find and read the task artifact JSON (paper_choice, game_choice, etc.)."""
    output_dir = trial_dir / "artifacts" / "app" / "output"
    if not output_dir.is_dir():
        return {}
    for f in sorted(output_dir.iterdir()):
        if f.suffix == ".json" and f.name != "manifest.json":
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                pass
    return {}


def build_structured_output(trial_dir: Path) -> dict | None:
    """Build a rich structured_output.json for one trial."""
    # --- Load sources ---
    result_file = trial_dir / "result.json"
    if not result_file.is_file():
        return None
    try:
        result = json.loads(result_file.read_text(encoding="utf-8"))
    except Exception:
        return None

    reward = (
        result.get("verifier_result", {}).get("rewards", {}).get("reward", 1.0)
    )
    reward = float(reward) if reward is not None else 0.0

    persona_meta_file = trial_dir / "persona_meta.json"
    persona_meta = {}
    if persona_meta_file.is_file():
        try:
            persona_meta = json.loads(persona_meta_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    artifact = extract_artifact_fields(trial_dir)
    persona_dims = load_persona_yaml(persona_meta)

    # --- Extract reason length ---
    reason = artifact.get("reason", "")
    reason_word_count = len(reason.split()) if reason else 0
    reason_char_count = len(reason)

    # --- Determine passed/failed ---
    passed = reward >= 0.5

    # --- Task-specific category (try multiple field names) ---
    task_category = (
        artifact.get("task_primary_category")
        or artifact.get("task_book_genre")
        or artifact.get("task_type_category")
        or artifact.get("task_genre")
        or artifact.get("task_category")
        or artifact.get("task_domain")
        or artifact.get("task_topic")
        or "task_output"
    )

    # --- Numerical task-specific fields ---
    task_numerical_facets = []
    for num_key in [
        "task_geek_rating", "task_rating", "task_average_rating",
        "task_points",
    ]:
        val = artifact.get(num_key)
        if val is not None:
            try:
                parsed = float(str(val).replace(" points", "").replace("/5", "").strip())
                task_numerical_facets.append({
                    "key": num_key,
                    "label": num_key.replace("task_", "").replace("_", " ").title(),
                    "role": "evidence",
                    "kind": "numerical",
                    "value": parsed,
                })
            except (ValueError, TypeError):
                pass

    # --- Rejected options (textual) ---
    rejected = artifact.get("task_rejected_options", "")

    # --- Extract persona traits ---
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

    # --- Persona numerical facets ---
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

    # --- Build contexts ---
    contexts = []

    # Context 1: Task outcome
    contexts.append({
        "key": "task_outcome.primary",
        "label": "Task outcome",
        "contextType": "task_outcome",
        "facets": [
            {
                "key": "outcome_status",
                "label": "Outcome status",
                "role": "primary",
                "kind": "categorical",
                "value": "passed" if passed else "failed",
            },
            {
                "key": "verifier_reward",
                "label": "Verifier reward",
                "role": "score",
                "kind": "numerical",
                "value": reward,
            },
        ],
    })

    # Context 2: Decision
    decision_facets = [
        {
            "key": "decision_outcome",
            "label": "Decision outcome",
            "role": "primary",
            "kind": "categorical",
            "value": artifact.get("decision_outcome", "selected"),
        },
        {
            "key": "basis_primary",
            "label": "Basis primary",
            "role": "primary",
            "kind": "categorical",
            "value": artifact.get("basis_primary", "unknown"),
        },
        {
            "key": "exploration_style",
            "label": "Exploration style",
            "role": "primary",
            "kind": "categorical",
            "value": artifact.get("exploration_style", "unknown"),
        },
        {
            "key": "task_category",
            "label": "Task category",
            "role": "primary",
            "kind": "categorical",
            "value": str(task_category) if task_category else "unknown",
        },
        {
            "key": "reasoning_length_words",
            "label": "Reasoning length (words)",
            "role": "score",
            "kind": "numerical",
            "value": float(reason_word_count),
        },
    ]
    decision_facets.extend(task_numerical_facets)

    if reason:
        decision_facets.append({
            "key": "reason_excerpt",
            "label": "Reason excerpt",
            "role": "explanation",
            "kind": "textual",
            "value": reason[:500],
        })

    if rejected:
        decision_facets.append({
            "key": "rejected_options",
            "label": "Rejected options",
            "role": "evidence",
            "kind": "textual",
            "value": rejected[:500],
        })

    contexts.append({
        "key": "decision.primary",
        "label": "Decision analysis",
        "contextType": "decision",
        "facets": decision_facets,
    })

    # Context 3: Persona analysis
    if trait_facets:
        contexts.append({
            "key": "persona.analysis",
            "label": "Persona analysis",
            "contextType": "persona_analysis",
            "facets": trait_facets,
        })

    # Context 4: Execution quality
    execution_facets = [
        {
            "key": "reasoning_length_chars",
            "label": "Reasoning length (chars)",
            "role": "score",
            "kind": "numerical",
            "value": float(reason_char_count),
        },
    ]
    if reason_word_count > 30:
        execution_facets.append({
            "key": "reason_detail_quality",
            "label": "Reason detail quality",
            "role": "score",
            "kind": "categorical",
            "value": "detailed" if reason_word_count > 50 else "moderate",
        })
    if persona_meta.get("display_name"):
        execution_facets.append({
            "key": "persona_name",
            "label": "Persona name",
            "role": "evidence",
            "kind": "textual",
            "value": persona_meta["display_name"],
        })

    contexts.append({
        "key": "execution.quality",
        "label": "Execution quality",
        "contextType": "execution",
        "facets": execution_facets,
    })

    return {
        "schemaVersion": "1.0",
        "artifactType": "personabench.trial_evaluation",
        "taskType": "web",
        "presenceCheck": {
            "passed": True,
            "requiredArtifacts": [],
            "missingArtifacts": [],
        },
        "sourceArtifacts": {},
        "contexts": contexts,
    }


def main():
    backfilled = 0
    skipped = 0
    errors = 0

    for job_dir in sorted(JOBS_DIR.iterdir()):
        if not job_dir.is_dir() or not job_dir.name.startswith(JOB_PREFIX):
            continue

        print(f"\n{'='*60}")
        print(f"Job: {job_dir.name}")

        for trial_dir in sorted(job_dir.iterdir()):
            if not trial_dir.is_dir() or trial_dir.name.startswith("."):
                continue

            verifier_dir = trial_dir / "verifier"
            target_file = verifier_dir / TRIAL_EVAL_FILENAME

            if not (trial_dir / "result.json").is_file():
                continue

            print(f"  Trial: {trial_dir.name}")

            payload = build_structured_output(trial_dir)
            if payload is None:
                print(f"    SKIP — no result.json or error")
                skipped += 1
                continue

            verifier_dir.mkdir(parents=True, exist_ok=True)
            target_file.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            ctx_count = len(payload["contexts"])
            facet_count = sum(len(c["facets"]) for c in payload["contexts"])
            reward = payload["contexts"][0]["facets"][1]["value"]
            print(f"    WROTE — {ctx_count} contexts, {facet_count} facets, reward={reward}")
            backfilled += 1

    print(f"\n{'='*60}")
    print(f"Done. Backfilled: {backfilled}, Skipped: {skipped}, Errors: {errors}")

    if backfilled > 0:
        print("\nDeleting stale aggregation.json files to force rebuild...")
        count = 0
        for job_dir in sorted(JOBS_DIR.iterdir()):
            if not job_dir.is_dir() or not job_dir.name.startswith(JOB_PREFIX):
                continue
            agg_file = job_dir / "aggregation.json"
            if agg_file.is_file():
                agg_file.unlink()
                print(f"  DELETED {job_dir.name}/aggregation.json")
                count += 1
        print(f"  ({count} files deleted)")


if __name__ == "__main__":
    main()
