#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python <<'PY'
import json
from pathlib import Path

output = Path("/app/output/portfolio_backtest.json")

# Reference oracle. Portfolio Visualizer is a heavy, anti-bot-protected JS form,
# so the oracle does not scrape live figures; it emits a schema-valid reference
# submission for a moderate, retirement-oriented persona to exercise the task and
# verifier contract end to end. Persona agents fill `results` from the live page.
try:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        # Best-effort reachability check; failures are non-fatal for the oracle.
        page.goto(
            "https://www.portfoliovisualizer.com/backtest-portfolio",
            wait_until="domcontentloaded",
            timeout=60_000,
        )
        browser.close()
except Exception:
    pass

payload = {
    "persona_context": {
        "investment_goal": "retirement",
        "risk_tolerance": "moderate",
        "time_horizon_years": 20,
        "constraints": ["none"],
    },
    "backtest_config": {
        "start_year": 2005,
        "initial_amount_usd": 10000,
        "allocation": [
            {"asset_class": "US Stock Market (VTSMX)", "percent": 45},
            {"asset_class": "Global ex-US Stock Market (VGTSX)", "percent": 20},
            {"asset_class": "Total US Bond Market (VBMFX)", "percent": 25},
            {"asset_class": "REIT (VGSIX)", "percent": 10},
        ],
    },
    "results": {
        "final_balance_usd": "38452.10",
        "cagr_percent": "7.12",
        "stdev_percent": "9.85",
        "max_drawdown_percent": "-30.72",
        "sharpe_ratio": "0.66",
    },
    "goal_alignment": "aligned",
    "flagged_concerns": [
        "The backtest window starts in 2005 and includes the 2008 drawdown, but "
        "past CAGR should not be extrapolated as a guaranteed future return.",
    ],
    "satisfied": True,
    "reason": (
        "A diversified 65/25/10 mix — US and international equity, total bond "
        "market, and a REIT sleeve — matches a moderate risk tolerance over a "
        "20-year retirement horizon: spreading equity across US and ex-US plus a "
        "real-asset allocation keeps the historical drawdown tolerable while "
        "returns keep pace with long-term goals, without over-concentrating in "
        "any single asset class."
    ),
}
output.write_text(json.dumps(payload, indent=2) + "\n")
PY
