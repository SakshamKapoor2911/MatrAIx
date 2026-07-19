import json
from pathlib import Path


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_persona_context_strips_explicit_rating_behavior():
    from persona.curation.existing_data.scripts.predict_amazon_persona_holdout_ratings import (
        persona_context,
    )

    context = persona_context(
        {
            "user_id": "USER_A",
            "evidence_profile": {
                "overview": (
                    "Enjoys technical books. Consistently gives five star ratings "
                    "to most products."
                ),
                "evidence_items": [
                    {
                        "evidence_item_id": "e1",
                        "broad_category_id": "product_interests",
                        "claim": "Prefers detailed technical manuals.",
                        "confidence": 0.8,
                        "evidence_type": "behavior",
                    }
                ],
            },
            "inferred_attributes": [
                {
                    "dimension_id": "domain",
                    "label": "Domain",
                    "category": "Expertise: Domains",
                    "value": "Books",
                    "confidence": 0.9,
                    "reasoning": "Buys advanced books.",
                }
            ],
        },
        mode="summary_dimensions",
        max_attributes=20,
        max_evidence_items=20,
    )

    assert "technical books" in context["evidence_profile"]["overview"]
    assert "five star" not in context["evidence_profile"]["overview"].lower()
    assert context["inferred_attributes"][0]["dimension_id"] == "domain"


def test_dry_run_writes_persona_grounded_prediction_prompt(tmp_path: Path):
    from persona.curation.existing_data.scripts.predict_amazon_persona_holdout_ratings import (
        main,
    )

    targets = tmp_path / "prediction_targets.jsonl"
    inference = tmp_path / "inferred_dimensions.jsonl"
    prompts = tmp_path / "persona_prediction_prompts.jsonl"
    output = tmp_path / "persona_predictions.jsonl"

    _write_jsonl(
        targets,
        [
            {
                "target_id": "USER_A::v000001",
                "user_id": "USER_A",
                "validation_index": 1,
                "cohort": "high_signal",
                "product_context": {
                    "source_category": "Books",
                    "parent_asin": "PARENT1",
                    "asin": "ASIN1",
                    "review_date": "2023-01-01",
                },
            }
        ],
    )
    _write_jsonl(
        inference,
        [
            {
                "user_id": "USER_A",
                "source": "amazon_reviews_2023",
                "inference_mode": "evidence_profile",
                "evidence_profile": {
                    "overview": "Prefers long-form technical books.",
                    "evidence_items": [
                        {
                            "evidence_item_id": "e1",
                            "broad_category_id": "product_interests",
                            "claim": "Reads technical books.",
                            "confidence": 0.9,
                            "evidence_type": "behavior",
                        }
                    ],
                },
                "inferred_attributes": [
                    {
                        "dimension_id": "domain",
                        "label": "Domain",
                        "category": "Expertise: Domains",
                        "value": "Books",
                        "confidence": 0.9,
                        "reasoning": "Evidence from book reviews.",
                    }
                ],
            }
        ],
    )

    status = main(
        [
            "--prediction-targets",
            str(targets),
            "--inference-output",
            str(inference),
            "--output",
            str(output),
            "--dry-run",
            "--dry-run-prompts-path",
            str(prompts),
        ]
    )

    rows = _read_jsonl(prompts)
    assert status == 0
    assert len(rows) == 1
    payload = rows[0]["user_payload"]
    assert payload["task"] == "predict_amazon_holdout_product_ratings_from_persona"
    assert payload["user_id"] == "USER_A"
    assert payload["targets"][0]["target_id"] == "USER_A::v000001"
    assert payload["targets"][0]["product_context"]["source_category"] == "Books"
    assert "true_rating" not in json.dumps(payload)
