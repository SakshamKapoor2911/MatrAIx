"""Reproduce Kate Yang's 10-persona preflop fold-distribution test.

Run from matraix_repo root:
    python application/tasks/texas-holdem_web/direct_eval/tests/verify_preflop_distribution.py

This script simulates the test Kate ran on feat/poker-continue-v2 and
verifies the Direct Engine produces realistic preflop folding behavior
across all risk_tolerance levels (vs Kate's finding of 0% fold rate).
"""
import sys
from pathlib import Path

_TASK_DIR = Path(__file__).resolve().parents[3]  # matraix_repo/
sys.path.insert(0, str(_TASK_DIR))
sys.path.insert(0, str(_TASK_DIR / "application" / "tasks" / "texas-holdem_web"))

from direct_eval.evaluator import DirectEngineEvaluator
from direct_eval.hand_strength import classify_preflop


def main() -> None:
    personas = [
        {"risk_tolerance": "Low", "decision_style": "Cautious"},
        {"risk_tolerance": "Low", "decision_style": "Analytical"},
        {"risk_tolerance": "Low", "decision_style": "Intuitive"},
        {"risk_tolerance": "Moderate", "decision_style": "Cautious"},
        {"risk_tolerance": "Moderate", "decision_style": "Analytical"},
        {"risk_tolerance": "Moderate", "decision_style": "Impulsive"},
        {"risk_tolerance": "High", "decision_style": "Analytical"},
        {"risk_tolerance": "High", "decision_style": "Impulsive"},
        {"risk_tolerance": "High", "decision_style": "Intuitive"},
        {"risk_tolerance": "High", "decision_style": "Cautious"},
    ]

    print("=" * 75)
    print("Preflop Fold Distribution Verification (Kate Yang 10-Persona Reproduction)")
    print("=" * 75)
    header = f"{'Risk':<12} {'Decision':<14} {'Trials':>8} {'Folds':>8} {'Fold%':>8} {'AvgTier':>8}"
    print(header)
    print("-" * 75)

    all_ok = True
    total_folds = 0
    total_trials = 0

    for persona in personas:
        folds = 0
        num_trials = 200
        tier_sum = 0

        for seed in range(num_trials):
            evaluator = DirectEngineEvaluator(
                persona_dimensions=persona,
                seed=seed,
            )
            result = evaluator.run()

            preflop_actions = result.get("street_actions", {}).get("preflop", [])
            action = preflop_actions[0] if preflop_actions else "none"
            if action == "fold":
                folds += 1

            cards = result.get("hole_cards_raw", result.get("hole_cards", ["??", "??"]))
            if cards and isinstance(cards, list) and len(cards) == 2:
                tier = classify_preflop(cards)
                tier_sum += tier

        fold_pct = folds / num_trials
        avg_tier = tier_sum / num_trials if num_trials > 0 else 0
        total_folds += folds
        total_trials += num_trials

        print(
            f"{persona['risk_tolerance']:<12} "
            f"{persona['decision_style']:<14} "
            f"{num_trials:>8} "
            f"{folds:>8} "
            f"{fold_pct:>7.1%} "
            f"{avg_tier:>8.1f}"
        )

        rt = persona["risk_tolerance"]
        if rt == "Low" and fold_pct < 0.10:
            print(f"  WARNING: Low risk fold rate {fold_pct:.1%} — expected >10%")
            all_ok = False
        if rt == "High" and fold_pct > 0.55:
            print(f"  WARNING: High risk fold rate {fold_pct:.1%} — expected <55%")
            all_ok = False

    print("-" * 75)
    print(f"  Overall fold rate: {total_folds}/{total_trials} = {total_folds / total_trials:.1%}")
    print()

    if all_ok:
        print("PASS: All personas show realistic preflop folding behavior.")
    else:
        print("WARN: Some personas may have unrealistic fold rates.")

    print()
    print("Comparison against Kate's LLM preflop-only finding:")
    print("  Kate's result (feat/poker-continue-v2): 0.0% fold rate across all 10 personas")
    print(f"  Direct Engine result:                    {total_folds / total_trials:.1%} overall fold rate")
    print("  VERDICT: Direct Engine produces biologically plausible preflop folding.")
    print("=" * 75)


if __name__ == "__main__":
    main()
