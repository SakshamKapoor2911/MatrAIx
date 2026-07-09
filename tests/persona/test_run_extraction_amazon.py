from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Mock vllm before importing anything that needs it
sys.modules["vllm"] = MagicMock()

# Add the scripts directory to the path so we can import the extraction script
ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "persona" / "human_extraction" / "scripts"))

import run_extraction_amazon as script  # noqa: E402


def test_canonical_allowed_value() -> None:
    dim = {
        "id": "gender_identity",
        "values": ["Woman", "Man", "Non-binary", "Self-described", "Prefer not to say"],
    }

    # Exact match
    assert script.canonical_allowed_value("Woman", dim) == "Woman"

    # Case insensitivity and whitespace normalization
    assert script.canonical_allowed_value("  non-binary ", dim) == "Non-binary"
    assert script.canonical_allowed_value("woman", dim) == "Woman"

    # Nullish values
    assert script.canonical_allowed_value(None, dim) is None
    assert script.canonical_allowed_value("none", dim) is None
    assert script.canonical_allowed_value("n/a", dim) is None

    # Invalid value
    assert script.canonical_allowed_value("UnknownGender", dim) is None


def test_evidence_is_quote() -> None:
    profile = "Amazon reviewer profile. The product is great. I bought this for my daughter last year."

    # Exact match (normalized)
    assert script.evidence_is_quote("great", profile) is True
    assert script.evidence_is_quote("bought this for my daughter", profile) is True

    # Case insensitive match
    assert script.evidence_is_quote("BOUGHT THIS", profile) is True

    # Too short
    assert script.evidence_is_quote("buy", profile) is False

    # Non-existent
    assert script.evidence_is_quote("not in profile", profile) is False

    # Nullish
    assert script.evidence_is_quote(None, profile) is False
    assert script.evidence_is_quote("", profile) is False


def test_is_sensitive_dimension() -> None:
    sensitive_dim = {
        "id": "user_age",
        "label": "User Age",
        "category": "Demographics",
        "description": "The age of the user",
    }
    non_sensitive_dim = {
        "id": "product_preference",
        "label": "Product preference",
        "category": "Interests",
        "description": "General product categories",
    }

    assert script.is_sensitive_dimension(sensitive_dim) is True
    assert script.is_sensitive_dimension(non_sensitive_dim) is False


def test_validate_model_field() -> None:
    profile = (
        "I am a female shopper and I love reading history books. I am 35 years old."
    )
    dim_gender = {
        "id": "gender_identity",
        "label": "Gender identity",
        "category": "Demographic: Core",
        "description": "Self-identified gender",
        "values": ["Woman", "Man"],
    }

    # Valid direct assignment for sensitive field
    field_valid = {
        "field_id": "gender_identity",
        "value": "Woman",
        "confidence": 0.9,
        "evidence": "I am a female shopper",
        "description": "The user is female.",
        "assignment_type": "direct",
    }
    validated = script.validate_model_field(field_valid, dim_gender, profile)
    assert validated["value"] == "Woman"
    assert validated["assignment_type"] == "direct"
    assert validated["confidence"] == 0.9
    assert validated["evidence"] == "I am a female shopper"

    # Invalid assignment type for sensitive field (e.g. structured_claim)
    field_invalid_type = field_valid.copy()
    field_invalid_type["assignment_type"] = "structured_claim"
    validated = script.validate_model_field(field_invalid_type, dim_gender, profile)
    assert validated["value"] is None
    assert validated["assignment_type"] == "unsupported"

    # Non-quote evidence
    field_non_quote = field_valid.copy()
    field_non_quote["evidence"] = "She bought books"
    validated = script.validate_model_field(field_non_quote, dim_gender, profile)
    assert validated["value"] is None
    assert validated["assignment_type"] == "unsupported"


def test_repair_jsonl_checkpoint(tmp_path: Path) -> None:
    test_file = tmp_path / "shard_00.jsonl"

    # 1. Test case: Completely valid JSONL file
    lines = [{"user_id": "1", "value": "A"}, {"user_id": "2", "value": "B"}]
    test_file.write_text(
        "\n".join(json.dumps(item) for item in lines) + "\n", encoding="utf-8"
    )

    removed, appended = script.repair_jsonl_checkpoint(test_file)
    assert removed == 0
    assert appended is False
    assert test_file.read_text(encoding="utf-8").count("\n") == 2

    # 2. Test case: Corrupt last line
    corrupt_line = '{"user_id": "3", "value": "C'  # Missing closing quote and bracket
    test_file.write_text(
        "\n".join(json.dumps(item) for item in lines) + "\n" + corrupt_line + "\n",
        encoding="utf-8",
    )

    removed, appended = script.repair_jsonl_checkpoint(test_file)
    assert removed > 0
    assert appended is False

    # Verify file is truncated and back to valid lines
    reread_lines = [
        json.loads(line) for line in test_file.read_text(encoding="utf-8").splitlines()
    ]
    assert reread_lines == lines

    # 3. Test case: Missing trailing newline
    test_file.write_text(
        "\n".join(json.dumps(item) for item in lines), encoding="utf-8"
    )
    removed, appended = script.repair_jsonl_checkpoint(test_file)
    assert removed == 0
    assert appended is True
    assert test_file.read_text(encoding="utf-8").endswith("\n")
