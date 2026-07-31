"""Integration unit tests for DirectEngineEvaluator and verifier compatibility."""
import json
from pathlib import Path

from direct_eval.evaluator import DirectEngineEvaluator


def test_direct_evaluator_runs_and_produces_valid_result():
    dims = {
        "risk_tolerance": "Low",
        "decision_style": "Analytical",
        "economic_motivation": "Cost-sensitive",
    }
    evaluator = DirectEngineEvaluator(persona_dimensions=dims, seed=42)
    result = evaluator.run()

    expected_seed = DirectEngineEvaluator._derive_persona_seed(dims, 42)

    assert result["game_id"] == "texas-holdem-heads-up-v1"
    assert result["seed"] == expected_seed
    assert len(result["hole_cards"]) == 2
    assert len(result["community_cards"]) <= 5
    assert result["winner"] in ("player", "opponent", "tie")
    assert isinstance(result["chip_delta"], int)
    assert result["risk_posture"] == "risk_averse"
    assert result["exploration_style"] == "deep_research"
    assert result["task_strategy_basis"] == "pot_control"
    assert len(result["reason"]) >= 20
    assert result["_mode"] == "direct"

    # Same dims + same seed -> same derived seed
    evaluator2 = DirectEngineEvaluator(persona_dimensions=dims, seed=42)
    result2 = evaluator2.run()
    assert result2["seed"] == expected_seed

    # Different dims + same seed -> different derived seed
    dims2 = {
        "risk_tolerance": "High",
        "decision_style": "Impulsive",
        "economic_motivation": "Premium-seeking",
    }
    evaluator3 = DirectEngineEvaluator(persona_dimensions=dims2, seed=42)
    result3 = evaluator3.run()
    assert result3["seed"] != expected_seed


def test_direct_evaluator_verifier_compliance(monkeypatch, tmp_path):
    dims = {
        "risk_tolerance": "High",
        "decision_style": "Impulsive",
        "economic_motivation": "Premium-seeking",
    }
    evaluator = DirectEngineEvaluator(persona_dimensions=dims, seed=1)
    result = evaluator.run()

    # Verify output schema fields (subset of full verifier check)
    assert result["game_id"] == "texas-holdem-heads-up-v1"
    assert isinstance(result["seed"], int)
    assert len(result["hole_cards"]) == 2
    assert len(result["community_cards"]) <= 5
    for street in ("preflop", "flop", "turn", "river"):
        assert isinstance(result["street_actions"].get(street, []), list)
    assert result["winner"] in ("player", "opponent", "tie")
    assert isinstance(result["chip_delta"], int)
    assert isinstance(result["pot_size"], int)
    assert result["risk_posture"] in ("risk_averse", "balanced", "risk_seeking", "opportunistic")
    assert result["exploration_style"] in ("deep_research", "compared_multiple", "quick_pick", "hesitant")
    assert result["task_strategy_basis"] in ("hand_strength", "pot_control", "bluff", "pot_odds")
    assert len(result["reason"]) >= 20
    assert result["_mode"] == "direct"

    # Mock persona.yaml input
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    persona_yaml = input_dir / "persona.yaml"
    persona_yaml.write_text(
        "dimensions:\n  risk_tolerance: High\n  decision_style: Impulsive\n  economic_motivation: Premium-seeking\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PERSONA_INPUT_DIR", str(input_dir))

    from tests.test_state import _compute_persona_consistency

    consistency = _compute_persona_consistency(result)
    assert consistency["score"] == 1.0
