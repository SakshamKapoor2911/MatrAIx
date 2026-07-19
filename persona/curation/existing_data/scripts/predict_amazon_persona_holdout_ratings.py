#!/usr/bin/env python3
"""Predict Amazon temporal-holdout ratings from constructed personas.

This is the LLM prediction half of the V1 Amazon persona validation flow. It
reads blind product-context-only targets produced by
`evaluate_amazon_persona_rating_holdout.py`, joins them to persona inference
outputs or persona YAML, and writes `target_id` / `predicted_rating` rows that
the evaluator can score.

The prompt intentionally excludes held-out review title/text and true ratings.
It also strips explicit rating-behavior summaries from persona text so the model
uses persona attributes rather than copied historical rating tendencies.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DEFAULT_TARGETS_PATH = (
    BASE_DIR
    / "raw"
    / "amazon_reviews_2023"
    / "persona_rating_holdout_eval"
    / "prediction_targets.jsonl"
)
DEFAULT_INFERENCE_PATH = (
    BASE_DIR
    / "raw"
    / "amazon_reviews_2023"
    / "persona_dimension_inference"
    / "inferred_dimensions.jsonl"
)
DEFAULT_PERSONA_YAML_PATH = (
    BASE_DIR
    / "raw"
    / "amazon_reviews_2023"
    / "persona_dimension_inference"
    / "inferred_dimensions.yaml"
)
DEFAULT_OUTPUT_PATH = (
    BASE_DIR
    / "raw"
    / "amazon_reviews_2023"
    / "persona_rating_holdout_eval"
    / "persona_predictions.jsonl"
)
DEFAULT_DRY_RUN_PROMPTS_PATH = (
    BASE_DIR
    / "raw"
    / "amazon_reviews_2023"
    / "persona_rating_holdout_eval"
    / "persona_prediction_prompts.jsonl"
)
DEFAULT_MODEL = os.environ.get("OPENAI_LLM_MODEL", "gpt-4.1-mini")

SYSTEM_PROMPT = """You predict future Amazon star ratings from a constructed persona.

Core task: predict how this user would rate each held-out product on a 1-5 star scale using only the provided persona and blind product context.

Rules:
- Do not assume access to the held-out review text, held-out review title, or true rating.
- Product context may include source category, ASIN, parent ASIN, and review date.
- Use the persona as the personalization signal. Avoid inventing demographics or facts not present in the persona.
- Do not use user cohort labels or explicit historical rating-behavior summaries.
- If product context is sparse, use the persona's interests, preferences, values, and lifestyle context cautiously.
- Return integer ratings only: 1, 2, 3, 4, or 5.
- Acknowledge uncertainty with confidence and concise rationale.

Return compact JSON only."""

RATING_BEHAVIOR_RE = re.compile(
    r"\b("
    r"rating|ratings|rate|rated|rates|rater|"
    r"star|stars|five[- ]?star|four[- ]?star|three[- ]?star|two[- ]?star|one[- ]?star|"
    r"5[- ]?star|4[- ]?star|3[- ]?star|2[- ]?star|1[- ]?star|"
    r"harsh reviewer|critical reviewer|generous reviewer|positive reviewer|"
    r"mostly positive|mostly negative|low[- ]?rating|high[- ]?rating|"
    r"average rating|rating distribution"
    r")\b",
    re.IGNORECASE,
)


def log(message: str) -> None:
    print(f"[amazon_persona_rating_predict] {message}", flush=True)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def iter_jsonl_or_gz(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]], append: bool = False) -> int:
    ensure_dir(path.parent)
    count = 0
    mode = "a" if append else "w"
    with open(path, mode, encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def compact_text(value: Any, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def contains_rating_behavior(value: Any) -> bool:
    return bool(RATING_BEHAVIOR_RE.search(str(value or "")))


def sanitize_rating_behavior_text(value: Any) -> str:
    """Drop sentences that explicitly summarize rating/star behavior."""
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    kept = [sentence for sentence in sentences if not contains_rating_behavior(sentence)]
    return " ".join(kept).strip()


def sanitize_dimension_value(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_rating_behavior_text(value)
    return value


def float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def int_rating_or_none(value: Any) -> int | None:
    parsed = float_or_none(value)
    if parsed is None:
        return None
    rating = int(round(parsed))
    if rating < 1 or rating > 5:
        return None
    return rating


def openai_request(
    payload: dict[str, Any],
    api_key: str,
    timeout: int = 180,
    retries: int = 6,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            error_body = err.read().decode("utf-8", errors="replace")
            if err.code in {429, 500, 502, 503, 504} and attempt < retries - 1:
                time.sleep(min(60, 2**attempt))
                continue
            raise RuntimeError(f"OpenAI API error {err.code}: {error_body[:1000]}") from err
        except urllib.error.URLError as err:
            if attempt < retries - 1:
                time.sleep(min(60, 2**attempt))
                continue
            raise RuntimeError(f"OpenAI request failed after retries: {err}") from err
    raise RuntimeError("OpenAI request failed after retries")


def parse_model_json(response: dict[str, Any]) -> dict[str, Any]:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as err:
        raise ValueError(f"Unexpected OpenAI response shape: {response}") from err
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return json.loads(content)


def load_personas(inference_path: Path) -> dict[str, dict[str, Any]]:
    personas = {}
    for row in iter_jsonl_or_gz(inference_path):
        user_id = row.get("user_id")
        if user_id:
            personas[str(user_id)] = row
    return personas


def load_yaml_personas(yaml_path: Path) -> dict[str, dict[str, Any]]:
    try:
        import yaml
    except ImportError as err:
        raise RuntimeError(
            "PyYAML is required for --persona-yaml. Install pyyaml or use --inference-output."
        ) from err

    with open(yaml_path, encoding="utf-8") as fh:
        document = yaml.safe_load(fh)
    if not isinstance(document, dict):
        raise ValueError(f"Unexpected persona YAML document shape: {yaml_path}")
    personas = {}
    for persona in document.get("personas") or []:
        if not isinstance(persona, dict):
            continue
        persona_id = persona.get("id")
        persona_name = persona.get("name")
        row = {
            "user_id": persona_name or persona_id,
            "source": "persona_yaml",
            "persona_yaml": persona,
        }
        if persona_name:
            personas[str(persona_name)] = row
        if persona_id:
            personas.setdefault(str(persona_id), row)
    return personas


def load_existing_predictions(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        str(row["target_id"])
        for row in iter_jsonl_or_gz(path)
        if row.get("target_id") and int_rating_or_none(row.get("predicted_rating")) is not None
    }


def load_targets(
    targets_path: Path,
    personas: dict[str, dict[str, Any]],
    max_targets: int,
    skip_target_ids: set[str],
) -> list[dict[str, Any]]:
    targets = []
    for row in iter_jsonl_or_gz(targets_path):
        target_id = row.get("target_id")
        user_id = row.get("user_id")
        if not target_id or not user_id:
            continue
        if str(target_id) in skip_target_ids:
            continue
        if str(user_id) not in personas:
            continue
        targets.append(row)
        if max_targets and len(targets) >= max_targets:
            break
    return targets


def batched(values: list[Any], batch_size: int) -> Iterator[list[Any]]:
    for index in range(0, len(values), batch_size):
        yield values[index : index + batch_size]


def persona_context(
    persona_row: dict[str, Any],
    mode: str,
    max_attributes: int,
    max_evidence_items: int,
) -> dict[str, Any]:
    yaml_persona = persona_row.get("persona_yaml")
    if isinstance(yaml_persona, dict):
        dimensions = yaml_persona.get("dimensions") or {}
        if isinstance(dimensions, dict):
            sanitized_dimensions = {}
            for key in sorted(dimensions):
                value = dimensions[key]
                if contains_rating_behavior(key) or contains_rating_behavior(value):
                    continue
                sanitized_value = sanitize_dimension_value(value)
                if sanitized_value not in (None, ""):
                    sanitized_dimensions[key] = sanitized_value
                if len(sanitized_dimensions) >= max_attributes:
                    break
            dimensions = sanitized_dimensions
        else:
            dimensions = {}
        return {
            "source": "persona_yaml",
            "persona_id": yaml_persona.get("id"),
            "user_id": yaml_persona.get("name") or persona_row.get("user_id"),
            "title": yaml_persona.get("title"),
            "description": compact_text(
                sanitize_rating_behavior_text(yaml_persona.get("description")),
                1800,
            ),
            "dimensions": dimensions,
            "sanitization": "explicit rating/star behavior removed from description and dimensions",
        }

    context: dict[str, Any] = {
        "user_id": persona_row.get("user_id"),
        "source": persona_row.get("source"),
        "inference_mode": persona_row.get("inference_mode"),
    }

    if mode in {"summary", "summary_dimensions"}:
        profile = persona_row.get("evidence_profile") or {}
        evidence_items = []
        for item in (profile.get("evidence_items") or [])[:max_evidence_items]:
            claim = sanitize_rating_behavior_text(item.get("claim"))
            if not claim:
                continue
            evidence_items.append(
                {
                    "id": item.get("evidence_item_id"),
                    "category": item.get("broad_category_id"),
                    "claim": compact_text(claim, 350),
                    "confidence": item.get("confidence"),
                    "type": item.get("evidence_type"),
                }
            )
        context["evidence_profile"] = {
            "overview": compact_text(
                sanitize_rating_behavior_text(profile.get("overview")),
                1200,
            ),
            "evidence_items": evidence_items,
        }

    if mode in {"dimensions", "summary_dimensions"}:
        attributes = []
        for attr in persona_row.get("inferred_attributes") or []:
            value = sanitize_dimension_value(attr.get("value"))
            reasoning = sanitize_rating_behavior_text(attr.get("reasoning"))
            if contains_rating_behavior(attr.get("dimension_id")) or value in (None, ""):
                continue
            attributes.append(
                {
                    "dimension_id": attr.get("dimension_id"),
                    "label": attr.get("label"),
                    "category": attr.get("category"),
                    "value": value,
                    "confidence": attr.get("confidence"),
                    "reasoning": compact_text(reasoning, 300),
                }
            )
            if len(attributes) >= max_attributes:
                break
        context["inferred_attributes"] = attributes

    return context


def prediction_payload(
    user_id: str,
    persona_row: dict[str, Any],
    targets: list[dict[str, Any]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    return {
        "task": "predict_amazon_holdout_product_ratings_from_persona",
        "user_id": user_id,
        "instructions": [
            "Predict each target's star rating using only constructed persona context and blind product context.",
            "Do not use held-out review text, held-out review title, or true rating.",
            "Do not use user cohort labels or explicit historical rating-behavior summaries.",
            "Return one prediction for every target_id in targets.",
            "predicted_rating must be an integer from 1 to 5.",
            "Use confidence between 0 and 1.",
            "Keep rationale short and cite persona signals, not hidden review content.",
        ],
        "output_json_schema": {
            "predictions": [
                {
                    "target_id": "target id copied exactly",
                    "predicted_rating": "integer 1-5",
                    "confidence": "number from 0 to 1",
                    "rationale": "short persona-grounded reason",
                    "persona_signals_used": ["short signal labels"],
                }
            ]
        },
        "persona": persona_context(
            persona_row,
            args.persona_mode,
            args.max_attributes,
            args.max_evidence_items,
        ),
        "targets": [
            {
                "target_id": target.get("target_id"),
                "validation_index": target.get("validation_index"),
                "product_context": target.get("product_context") or {},
            }
            for target in targets
        ],
    }


def request_payload(user_payload: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    return {
        "model": args.model,
        "temperature": args.temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    }


def validate_predictions(
    model_output: dict[str, Any],
    targets: list[dict[str, Any]],
    method_name: str,
    model: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    valid_target_ids = {str(target["target_id"]) for target in targets}
    target_by_id = {str(target["target_id"]): target for target in targets}
    predictions = model_output.get("predictions")
    if not isinstance(predictions, list):
        return [], [
            {
                "target_id": target_id,
                "reason": "missing_predictions_list",
                "model_output": model_output,
            }
            for target_id in sorted(valid_target_ids)
        ]

    accepted = []
    rejected = []
    seen = set()
    for prediction in predictions:
        if not isinstance(prediction, dict):
            rejected.append({"item": prediction, "reason": "prediction_not_object"})
            continue
        target_id = str(prediction.get("target_id") or "")
        if target_id not in valid_target_ids:
            rejected.append({"item": prediction, "reason": "unknown_target_id"})
            continue
        if target_id in seen:
            rejected.append({"item": prediction, "reason": "duplicate_target_id"})
            continue
        rating = int_rating_or_none(prediction.get("predicted_rating"))
        if rating is None:
            rejected.append({"item": prediction, "reason": "invalid_predicted_rating"})
            continue
        target = target_by_id[target_id]
        accepted.append(
            {
                "target_id": target_id,
                "user_id": target.get("user_id"),
                "prediction_method": method_name,
                "model": model,
                "predicted_rating": rating,
                "confidence": float_or_none(prediction.get("confidence")),
                "rationale": compact_text(prediction.get("rationale"), 600),
                "persona_signals_used": prediction.get("persona_signals_used") or [],
            }
        )
        seen.add(target_id)

    for target_id in sorted(valid_target_ids - seen):
        rejected.append({"target_id": target_id, "reason": "missing_target_prediction"})
    return accepted, rejected


def write_dry_run_prompts(
    targets: list[dict[str, Any]],
    personas: dict[str, dict[str, Any]],
    args: argparse.Namespace,
) -> int:
    rows = []
    targets_by_user: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for target in targets:
        targets_by_user[str(target["user_id"])].append(target)
    for user_id, user_targets in sorted(targets_by_user.items()):
        persona_row = personas[user_id]
        for batch_index, target_batch in enumerate(
            batched(user_targets, args.targets_per_call),
            start=1,
        ):
            rows.append(
                {
                    "user_id": user_id,
                    "batch_index": batch_index,
                    "target_count": len(target_batch),
                    "system_prompt": SYSTEM_PROMPT,
                    "user_payload": prediction_payload(user_id, persona_row, target_batch, args),
                }
            )
    return write_jsonl(args.dry_run_prompts_path, rows)


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prediction-targets", type=Path, default=DEFAULT_TARGETS_PATH)
    parser.add_argument(
        "--persona-yaml",
        type=Path,
        default=None,
        help=(
            "Persona YAML with top-level personas list. Amazon exports should use "
            "raw user_id as persona name. When supplied, this is used instead of "
            "--inference-output."
        ),
    )
    parser.add_argument("--inference-output", type=Path, default=DEFAULT_INFERENCE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--persona-mode",
        choices=("dimensions", "summary", "summary_dimensions"),
        default="summary_dimensions",
        help="Persona representation included in the prediction prompt.",
    )
    parser.add_argument("--prediction-method-name", default="persona_summary_dimensions")
    parser.add_argument("--targets-per-call", type=int, default=20)
    parser.add_argument("--max-targets", type=int, default=0, help="0 means all targets.")
    parser.add_argument("--max-attributes", type=int, default=80)
    parser.add_argument("--max-evidence-items", type=int, default=40)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output instead of resuming from existing target_ids.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write prompts and exit without calling the OpenAI API.",
    )
    parser.add_argument(
        "--dry-run-prompts-path",
        type=Path,
        default=DEFAULT_DRY_RUN_PROMPTS_PATH,
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    if not args.prediction_targets.exists():
        raise FileNotFoundError(f"Prediction targets not found: {args.prediction_targets}")
    if args.persona_yaml:
        if not args.persona_yaml.exists():
            raise FileNotFoundError(f"Persona YAML not found: {args.persona_yaml}")
    elif not args.inference_output.exists():
        raise FileNotFoundError(f"Inference output not found: {args.inference_output}")
    if args.targets_per_call <= 0:
        raise ValueError("--targets-per-call must be positive")

    personas = (
        load_yaml_personas(args.persona_yaml)
        if args.persona_yaml
        else load_personas(args.inference_output)
    )
    if not personas:
        source = args.persona_yaml or args.inference_output
        raise ValueError(f"No personas loaded from {source}")

    skip_target_ids = set() if args.overwrite else load_existing_predictions(args.output)
    targets = load_targets(
        args.prediction_targets,
        personas,
        args.max_targets,
        skip_target_ids,
    )
    log(
        f"Loaded {len(personas):,} persona lookup keys and {len(targets):,} "
        f"pending targets from {args.prediction_targets}"
    )

    if args.dry_run:
        count = write_dry_run_prompts(targets, personas, args)
        log(f"Wrote {count:,} dry-run prompts: {args.dry_run_prompts_path}")
        return 0

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required unless --dry-run is used.")

    targets_by_user: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for target in targets:
        targets_by_user[str(target["user_id"])].append(target)

    append = not args.overwrite
    total_written = 0
    total_rejected = 0
    for user_index, (user_id, user_targets) in enumerate(
        sorted(targets_by_user.items()),
        start=1,
    ):
        persona_row = personas[user_id]
        for batch_index, target_batch in enumerate(
            batched(user_targets, args.targets_per_call),
            start=1,
        ):
            payload = request_payload(
                prediction_payload(user_id, persona_row, target_batch, args),
                args,
            )
            response = openai_request(payload, api_key)
            model_output = parse_model_json(response)
            accepted, rejected = validate_predictions(
                model_output,
                target_batch,
                args.prediction_method_name,
                args.model,
            )
            if accepted:
                total_written += write_jsonl(args.output, accepted, append=append)
                append = True
            total_rejected += len(rejected)
            log(
                f"user {user_index:,}/{len(targets_by_user):,} {user_id} "
                f"batch {batch_index}: wrote {len(accepted):,}, rejected {len(rejected):,}"
            )

    log(
        f"Wrote {total_written:,} predictions to {args.output}; "
        f"rejected predictions/items: {total_rejected:,}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
