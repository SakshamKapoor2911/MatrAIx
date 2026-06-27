#!/usr/bin/env python3
"""Render Amazon review persona inference JSONL outputs as Markdown.

This is for inspecting pilot runs. It does not require API access. If user
histories and the evidence mapping are provided, it also estimates cost from
serialized prompt/output character counts. Exact billed tokens are unavailable
unless the inference script persists API usage metadata.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
REPO_ROOT = BASE_DIR.parents[2]
DEFAULT_INFERENCE_PATH = (
    BASE_DIR
    / "raw"
    / "amazon_reviews_2023"
    / "persona_dimension_inference"
    / "inferred_dimensions_pilot_2users_dpc100.jsonl"
)
DEFAULT_PROFILE_PATH = (
    BASE_DIR
    / "raw"
    / "amazon_reviews_2023"
    / "persona_dimension_inference"
    / "evidence_profiles_pilot_2users_dpc100.jsonl"
)
DEFAULT_OUTPUT_PATH = (
    BASE_DIR
    / "raw"
    / "amazon_reviews_2023"
    / "persona_dimension_inference"
    / "pilot_2users_dpc100_readable.md"
)


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def compact(value: Any, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def load_inference_module() -> Any:
    module_path = SCRIPT_DIR / "infer_amazon_review_dimensions.py"
    spec = importlib.util.spec_from_file_location("infer_amazon_review_dimensions", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load inference module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def estimate_cost(
    rows: list[dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
    histories_path: Path,
    evidence_mapping_path: Path,
    schema_path: Path,
    model: str,
    dimensions_per_call: int,
    max_reviews_per_user: int,
    max_review_text_chars: int,
    max_review_context_chars: int,
    input_price_per_million: float,
    output_price_per_million: float,
) -> dict[str, Any]:
    infer = load_inference_module()
    mapping = infer.load_evidence_mapping(evidence_mapping_path)
    dimensions = infer.load_schema(schema_path)
    dimensions = infer.filter_amazon_supported_dimensions(dimensions, mapping)
    user_ids = {str(row.get("user_id")) for row in rows}

    class Args:
        pass

    args = Args()
    args.max_reviews_per_user = max_reviews_per_user
    args.max_review_text_chars = max_review_text_chars
    args.max_review_context_chars = max_review_context_chars
    args.dimensions_per_call = dimensions_per_call

    stage1_chars = 0
    stage2_chars = 0
    for history in iter_jsonl(histories_path):
        user_id = str(history.get("user_id"))
        if user_id not in user_ids:
            continue
        review_context = infer.build_review_context(
            history.get("reviews") or [],
            args.max_reviews_per_user,
            args.max_review_text_chars,
            args.max_review_context_chars,
        )
        stage1_payload = {
            "model": model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": infer.EVIDENCE_PROFILE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        infer.evidence_profile_payload(history, review_context, mapping),
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        stage1_chars += len(json.dumps(stage1_payload, ensure_ascii=False))
        evidence_profile = profiles[user_id]["evidence_profile"]
        for batch in infer.batched(dimensions, args.dimensions_per_call):
            stage2_payload = {
                "model": model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": infer.SCHEMA_MAPPING_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(
                            infer.schema_mapping_payload(history, batch, evidence_profile),
                            ensure_ascii=False,
                        ),
                    },
                ],
            }
            stage2_chars += len(json.dumps(stage2_payload, ensure_ascii=False))

    output_chars = sum(len(json.dumps(row, ensure_ascii=False)) for row in rows)
    output_chars += sum(len(json.dumps(row, ensure_ascii=False)) for row in profiles.values())
    input_tokens_mid = (stage1_chars + stage2_chars) / 4
    input_tokens_high = (stage1_chars + stage2_chars) / 3.5
    output_tokens_mid = output_chars / 4
    output_tokens_high = output_chars / 3.5
    cost_mid = (
        input_tokens_mid / 1_000_000 * input_price_per_million
        + output_tokens_mid / 1_000_000 * output_price_per_million
    )
    cost_high = (
        input_tokens_high / 1_000_000 * input_price_per_million
        + output_tokens_high / 1_000_000 * output_price_per_million
    )
    return {
        "stage1_chars": stage1_chars,
        "stage2_chars": stage2_chars,
        "input_chars": stage1_chars + stage2_chars,
        "output_chars": output_chars,
        "input_tokens_mid": input_tokens_mid,
        "input_tokens_high": input_tokens_high,
        "output_tokens_mid": output_tokens_mid,
        "output_tokens_high": output_tokens_high,
        "cost_mid": cost_mid,
        "cost_high": cost_high,
    }


def render_markdown(
    rows: list[dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
    cost: dict[str, Any] | None,
    args: argparse.Namespace,
) -> str:
    lines = [
        "# Amazon Persona Inference Pilot",
        "",
        (
            "This report renders evidence-profile inference output in a readable "
            "format. Missing schema dimensions mean `unknown / not inferred from "
            "available Amazon review evidence`, not negative evidence."
        ),
        "",
        "## Run Summary",
        "",
        "| Setting | Value |",
        "| --- | --- |",
        f"| Inference mode | {args.inference_mode} |",
        f"| Dimensions per call | {args.dimensions_per_call} |",
        f"| Users | {len(rows)} |",
        f"| Output JSONL | `{args.inference_output.name}` |",
        f"| Evidence profiles JSONL | `{args.evidence_profiles.name}` |",
        "",
    ]
    if cost:
        lines.extend(
            [
                "## Estimated Cost",
                "",
                (
                    "The script estimates cost from serialized prompt/output character "
                    "counts. Exact billed tokens require API usage metadata. Pricing "
                    f"assumption: `{args.model}` at `${args.input_price_per_million:g} / "
                    f"1M input tokens` and `${args.output_price_per_million:g} / 1M "
                    "output tokens`."
                ),
                "",
                "| Metric | Estimate |",
                "| --- | ---: |",
                f"| Stage 1 input chars | {cost['stage1_chars']:,.0f} |",
                f"| Stage 2 input chars | {cost['stage2_chars']:,.0f} |",
                f"| Total input chars | {cost['input_chars']:,.0f} |",
                f"| Stored output chars | {cost['output_chars']:,.0f} |",
                (
                    f"| Approx input tokens | {cost['input_tokens_mid']:,.0f}-"
                    f"{cost['input_tokens_high']:,.0f} |"
                ),
                (
                    f"| Approx output tokens | {cost['output_tokens_mid']:,.0f}-"
                    f"{cost['output_tokens_high']:,.0f} |"
                ),
                f"| Estimated total cost | `${cost['cost_mid']:.3f}-${cost['cost_high']:.3f}` |",
                "",
            ]
        )
    lines.extend(
        [
            "## User Summary",
            "",
            "| User ID | Review count | Evidence items | Inferred attributes | Rejected attributes | Requests |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in rows:
        lines.append(
            f"| `{row.get('user_id')}` | {row.get('review_count')} | "
            f"{row.get('evidence_item_count')} | {len(row.get('inferred_attributes', []))} | "
            f"{len(row.get('rejected_attributes', []))} | {row.get('request_count')} |"
        )
    lines.append("")

    for row in rows:
        user_id = str(row.get("user_id"))
        profile = (profiles.get(user_id) or {}).get("evidence_profile") or row.get(
            "evidence_profile", {}
        )
        lines.extend(
            [
                f"## User `{user_id}`",
                "",
                f"- Review count: {row.get('review_count')}",
                f"- Review context count: {row.get('review_context_count')}",
                f"- Evidence items: {row.get('evidence_item_count')}",
                f"- Inferred attributes: {len(row.get('inferred_attributes', []))}",
                f"- Rejected attributes: {len(row.get('rejected_attributes', []))}",
                "",
            ]
        )
        if profile.get("overview"):
            lines.extend(["### Evidence Profile Overview", "", profile["overview"], ""])
        if profile.get("evidence_items"):
            lines.extend(["### Evidence Items", ""])
            for item in profile["evidence_items"]:
                lines.append(
                    f"- `{item.get('evidence_item_id')}` **{item.get('broad_category_id', '')}** "
                    f"({item.get('evidence_type', '')}, confidence {item.get('confidence')}): "
                    f"{item.get('claim')}"
                )
                for support in (item.get("support") or [])[:2]:
                    lines.append(
                        f"  - `{support.get('review_id')}`: \"{compact(support.get('quote'), 220)}\""
                    )
            lines.append("")

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for attr in row.get("inferred_attributes", []):
            grouped[attr.get("category", "Uncategorized")].append(attr)
        lines.extend(["### Inferred Attributes", ""])
        for category in sorted(grouped):
            lines.extend(
                [
                    f"#### {category}",
                    "",
                    "| Dimension | Value | Confidence | Evidence | Rationale |",
                    "| --- | --- | ---: | --- | --- |",
                ]
            )
            for attr in sorted(grouped[category], key=lambda item: item.get("label", "")):
                dimension = f"{attr.get('label')} (`{attr.get('dimension_id')}`)"
                value = str(attr.get("value", "")).replace("|", "\\|")
                evidence = ", ".join(
                    f"`{item}`"
                    for item in (attr.get("evidence_item_ids") or attr.get("evidence_review_ids") or [])
                )
                rationale = compact(attr.get("reasoning"), 180).replace("|", "\\|")
                lines.append(
                    f"| {dimension} | {value} | {attr.get('confidence')} | {evidence} | {rationale} |"
                )
            lines.append("")

        rejected = row.get("rejected_attributes") or []
        if rejected:
            lines.extend(["### Rejected Attributes", ""])
            for rejected_item in rejected[:10]:
                item = rejected_item.get("item")
                if isinstance(item, dict):
                    item_desc = item.get("dimension_id") or item.get("value") or compact(item, 160)
                else:
                    item_desc = compact(item, 160)
                lines.append(f"- {rejected_item.get('reason')}: `{item_desc}`")
            if len(rejected) > 10:
                lines.append(f"- ... {len(rejected) - 10} more")
            lines.append("")
    return "\n".join(lines) + "\n"


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inference-output", type=Path, default=DEFAULT_INFERENCE_PATH)
    parser.add_argument("--evidence-profiles", type=Path, default=DEFAULT_PROFILE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--user-histories", type=Path, default=None)
    parser.add_argument(
        "--schema-path",
        type=Path,
        default=REPO_ROOT / "persona" / "schema" / "dimensions.json",
    )
    parser.add_argument(
        "--evidence-mapping-path",
        type=Path,
        default=BASE_DIR / "amazon_review_evidence_mapping.json",
    )
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--inference-mode", default="evidence_profile")
    parser.add_argument("--dimensions-per-call", type=int, default=100)
    parser.add_argument("--max-reviews-per-user", type=int, default=80)
    parser.add_argument("--max-review-text-chars", type=int, default=900)
    parser.add_argument("--max-review-context-chars", type=int, default=70_000)
    parser.add_argument("--input-price-per-million", type=float, default=0.75)
    parser.add_argument("--output-price-per-million", type=float, default=4.50)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    rows = list(iter_jsonl(args.inference_output))
    profiles = {str(row.get("user_id")): row for row in iter_jsonl(args.evidence_profiles)}
    cost = None
    if args.user_histories:
        cost = estimate_cost(
            rows,
            profiles,
            args.user_histories,
            args.evidence_mapping_path,
            args.schema_path,
            args.model,
            args.dimensions_per_call,
            args.max_reviews_per_user,
            args.max_review_text_chars,
            args.max_review_context_chars,
            args.input_price_per_million,
            args.output_price_per_million,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_markdown(rows, profiles, cost, args), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
