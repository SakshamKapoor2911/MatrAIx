from __future__ import annotations

import json
import numbers
import os
from pathlib import Path

OUTPUT = Path("/app/output/portfolio_backtest.json")

GOALS = {"retirement", "wealth_growth", "income_generation", "capital_preservation"}
RISK = {"conservative", "moderate", "aggressive"}
ALIGNMENT = {"aligned", "partially_aligned", "misaligned"}


def _load() -> dict:
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"
    data = json.loads(OUTPUT.read_text())
    assert isinstance(data, dict), "root must be an object"
    return data


def _as_number(value) -> float:
    """Accept a real number or a numeric string as shown on the site."""
    if isinstance(value, bool):  # bool is a subclass of int; reject it here
        raise AssertionError("expected a numeric value, got a bool")
    if isinstance(value, numbers.Real):
        return float(value)
    assert isinstance(value, str), "value must be a number or numeric string"
    cleaned = value.strip().replace(",", "").replace("$", "").replace("%", "")
    return float(cleaned)


def _verifier_dir() -> Path:
    base = (
        os.environ.get("HARBOR_VERIFIER_DIR")
        or os.environ.get("PERSONABENCH_VERIFIER_DIR")
        or "/logs/verifier"
    )
    path = Path(base)
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        path = Path(__file__).resolve().parent.parent / "verifier"
        path.mkdir(parents=True, exist_ok=True)
        return path


def _write_structured_output(payload: dict[str, object]) -> None:
    path = _verifier_dir() / "structured_output.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_output_exists():
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"


def test_persona_context():
    data = _load()
    ctx = data.get("persona_context")
    assert isinstance(ctx, dict), "persona_context must be an object"

    assert ctx.get("investment_goal") in GOALS, (
        f"investment_goal must be one of {sorted(GOALS)}"
    )
    assert ctx.get("risk_tolerance") in RISK, (
        f"risk_tolerance must be one of {sorted(RISK)}"
    )

    horizon = ctx.get("time_horizon_years")
    assert isinstance(horizon, numbers.Real) and not isinstance(horizon, bool), (
        "time_horizon_years must be a number"
    )
    assert 0 < float(horizon) <= 100, "time_horizon_years must be in (0, 100]"

    constraints = ctx.get("constraints")
    assert isinstance(constraints, list) and constraints, (
        "constraints must be a non-empty list (use ['none'] if there are none)"
    )
    assert all(isinstance(c, str) and c.strip() for c in constraints), (
        "each constraint must be a non-empty string"
    )


def test_backtest_config():
    data = _load()
    cfg = data.get("backtest_config")
    assert isinstance(cfg, dict), "backtest_config must be an object"

    start_year = cfg.get("start_year")
    assert isinstance(start_year, int) and not isinstance(start_year, bool), (
        "start_year must be an integer"
    )
    assert 1970 <= start_year <= 2026, "start_year must be a plausible year"

    initial = cfg.get("initial_amount_usd")
    assert isinstance(initial, numbers.Real) and not isinstance(initial, bool), (
        "initial_amount_usd must be a number"
    )
    assert float(initial) > 0, "initial_amount_usd must be positive"

    allocation = cfg.get("allocation")
    assert isinstance(allocation, list) and len(allocation) >= 2, (
        "allocation must list at least two asset classes"
    )
    total = 0.0
    for item in allocation:
        assert isinstance(item, dict), "each allocation entry must be an object"
        asset = item.get("asset_class")
        assert isinstance(asset, str) and asset.strip(), (
            "asset_class must be a non-empty string"
        )
        pct = item.get("percent")
        assert isinstance(pct, numbers.Real) and not isinstance(pct, bool), (
            "percent must be a number"
        )
        assert 0 <= float(pct) <= 100, "each percent must be within 0..100"
        total += float(pct)
    assert abs(total - 100.0) <= 0.5, f"allocation percents must sum to 100 (got {total})"


def test_results():
    data = _load()
    results = data.get("results")
    assert isinstance(results, dict), "results must be an object"
    for key in (
        "final_balance_usd",
        "cagr_percent",
        "stdev_percent",
        "max_drawdown_percent",
        "sharpe_ratio",
    ):
        assert key in results, f"results.{key} is required"
        # Must parse as a number; raises AssertionError/ValueError otherwise.
        _as_number(results[key])


def _equity_weight(allocation: list[dict]) -> float:
    """Rough equity exposure: asset classes that read as stock/equity/REIT."""
    equity = 0.0
    for item in allocation:
        name = str(item.get("asset_class", "")).lower()
        if any(k in name for k in ("stock", "equit", "reit", "emerging", "small cap", "large cap")):
            equity += float(item.get("percent", 0) or 0)
    return equity


def test_judgement():
    """Validate the persona's judgement fields and emit structured_output.json."""
    data = _load()

    goal_alignment = data.get("goal_alignment")
    assert goal_alignment in ALIGNMENT, (
        f"goal_alignment must be one of {sorted(ALIGNMENT)}"
    )

    flagged = data.get("flagged_concerns")
    assert isinstance(flagged, list), "flagged_concerns must be a list"
    assert all(isinstance(c, str) and c.strip() for c in flagged), (
        "each flagged concern must be a non-empty string"
    )

    assert isinstance(data.get("satisfied"), bool), "satisfied must be a boolean"

    reason = data.get("reason")
    assert isinstance(reason, str) and len(reason.strip()) >= 10, (
        "reason must be a sentence explaining the fit"
    )

    ctx = data.get("persona_context") or {}
    cfg = data.get("backtest_config") or {}
    investment_goal = str(ctx.get("investment_goal", ""))
    risk_tolerance = str(ctx.get("risk_tolerance", ""))
    allocation = cfg.get("allocation") or []
    equity_weight = _equity_weight(allocation)
    disclosure_present = "yes" if len(flagged) > 0 else "no"
    satisfaction = "yes" if data.get("satisfied") else "no"
    alloc_summary = ", ".join(
        f"{item.get('asset_class')} {item.get('percent')}%" for item in allocation
    )
    disclosure_text = " | ".join(flagged) if flagged else "No risk concerns were raised."

    # Shared web `decision` contract (application/task-spec/web): a persona who
    # is satisfied adopts the allocation (selected); otherwise they reject it.
    # The basis for a portfolio choice is always fit-to-goal/risk. Finance-only
    # signals are kept behind the `task_` prefix per the contributor extension
    # rules; `risk_posture` reuses the recommended standard facet.
    decision_outcome = "selected" if data.get("satisfied") else "rejected"
    decision_subject_id = f"alloc_eq{round(equity_weight)}"

    contexts: list[dict[str, object]] = [
        {
            "key": "task_outcome.primary",
            "label": "Task outcome",
            "contextType": "task_outcome",
            "facets": [
                {"key": "outcome_status", "label": "Outcome status", "role": "primary", "kind": "categorical", "value": "passed"},
                {"key": "goal_completion_bucket", "label": "Goal completion bucket", "role": "primary", "kind": "categorical", "value": "complete"},
                {"key": "verifier_mode", "label": "Verifier mode", "role": "evidence", "kind": "categorical", "value": "artifact_schema"},
                {"key": "primary_failure_reason", "label": "Primary failure reason", "role": "primary", "kind": "categorical", "value": "none"},
                {"key": "outcome_explanation", "label": "Outcome explanation", "role": "explanation", "kind": "textual", "explainsFacetKey": "outcome_status", "value": f"The persona built a {alloc_summary} portfolio, ran the backtest, and saved a valid {OUTPUT.name} artifact."},
            ],
        },
        {
            "key": "web_artifact.primary",
            "label": "Web artifact",
            "contextType": "web_artifact",
            "facets": [
                {"key": "artifact_type", "label": "Artifact type", "role": "primary", "kind": "categorical", "value": "task_submission"},
                {"key": "artifact_status", "label": "Artifact status", "role": "primary", "kind": "categorical", "value": "correct"},
                {"key": "artifact_evidence", "label": "Artifact evidence", "role": "explanation", "kind": "textual", "explainsFacetKey": "artifact_status", "value": f"Backtest results captured: {json.dumps(data.get('results', {}), ensure_ascii=False)}."},
            ],
        },
        {
            "key": "decision.primary",
            "label": "Portfolio decision",
            "contextType": "decision",
            "facets": [
                # Standard web `decision` facets (keep keys exactly as specified).
                {"key": "decision_outcome", "label": "Decision outcome", "role": "primary", "kind": "categorical", "value": decision_outcome},
                {"key": "basis_primary", "label": "Primary basis", "role": "primary", "kind": "categorical", "value": "fit"},
                {"key": "reason", "label": "Reason", "role": "explanation", "kind": "textual", "explainsFacetKey": "decision_outcome", "value": reason.strip()},
                {"key": "decision_subject_label", "label": "Chosen allocation", "role": "evidence", "kind": "textual", "value": alloc_summary},
                {"key": "decision_subject_id", "label": "Allocation id", "role": "evidence", "kind": "categorical", "value": decision_subject_id},
                # Recommended standard extra facet.
                {"key": "risk_posture", "label": "Risk posture", "role": "primary", "kind": "categorical", "value": risk_tolerance},
                # Task-specific finance signals (task_ prefix per extension rules).
                {"key": "task_goal_alignment", "label": "Goal alignment", "role": "evidence", "kind": "categorical", "value": goal_alignment},
                {"key": "task_investment_goal", "label": "Investment goal", "role": "evidence", "kind": "categorical", "value": investment_goal},
                {"key": "task_equity_weight_percent", "label": "Equity weight (%)", "role": "score", "kind": "numerical", "value": equity_weight},
            ],
        },
        {
            "key": "risk_disclosure.primary",
            "label": "Risk disclosure",
            "contextType": "risk_disclosure",
            "facets": [
                {"key": "disclosure_present", "label": "Disclosure present", "role": "primary", "kind": "categorical", "value": disclosure_present},
                {"key": "risk_tolerance", "label": "Risk tolerance", "role": "primary", "kind": "categorical", "value": risk_tolerance},
                {"key": "disclosure_text", "label": "Disclosure text", "role": "explanation", "kind": "textual", "explainsFacetKey": "disclosure_present", "value": disclosure_text},
            ],
        },
        {
            "key": "user_feedback.primary",
            "label": "User feedback",
            "contextType": "user_feedback",
            "facets": [
                {"key": "satisfaction", "label": "Satisfaction", "role": "primary", "kind": "categorical", "value": satisfaction},
                {"key": "goal_alignment", "label": "Goal alignment", "role": "primary", "kind": "categorical", "value": goal_alignment},
                {"key": "feedback_reason", "label": "Feedback reason", "role": "explanation", "kind": "textual", "explainsFacetKey": "satisfaction", "value": reason.strip()},
            ],
        },
    ]

    _write_structured_output(
        {
            "schemaVersion": "1.0",
            "artifactType": "matraix.trial_evaluation",
            "taskType": "web",
            "presenceCheck": {
                "passed": True,
                "requiredArtifacts": [OUTPUT.name],
                "missingArtifacts": [],
            },
            "sourceArtifacts": {"taskOutput": str(OUTPUT)},
            "contexts": contexts,
        }
    )
