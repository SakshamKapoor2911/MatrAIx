from __future__ import annotations

import json
from pathlib import Path

from persona.post_process.quality_filter.conflicts import compile_hard_rules


REPO_ROOT = Path(__file__).resolve().parents[3]
RULES_PATH = REPO_ROOT / "persona/post_process/quality_filter/contradictions.json"
SCHEMA_PATH = REPO_ROOT / "persona/schema/dimensions.json"


def test_all_contradiction_rules_compile_against_schema() -> None:
    rules_document = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    compiled = compile_hard_rules(rules_document, schema["dimensions"])

    assert len(compiled) == len(rules_document["conditional_masks"])
    assert len({rule.rule_id for rule in compiled}) == len(compiled)