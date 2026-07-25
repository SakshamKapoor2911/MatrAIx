# Backtest portfolio asset allocation (browser-use)

PersonaBench **browser-use** web task on a live public finance site. Chromium is
driven by the [browser-use](https://github.com/browser-use/browser-use) agent
loop (DOM + optional vision) against the Portfolio Visualizer *Backtest
Portfolio* tool.

- URL: https://www.portfoliovisualizer.com/backtest-portfolio
- Output: `/app/output/portfolio_backtest.json`

**Study goal:** how different personas construct and evaluate investment
portfolios — their risk-return trade-offs, goal alignment, and how they read
historical performance. Each persona assumes its own financial situation, inputs
details gradually, and flags unrealistic or overly optimistic projections.

See [Application Tasks](../README.md) for contribution guidance and
[web-interaction.md](../../web-interaction.md) for the shared web contract.

## Persona attributes exercised

| Dimension | Source |
|-----------|--------|
| Socioeconomic band (income, investable assets) | persona schema |
| Age band (age, time horizon) | persona schema |
| Communication style | persona schema |
| `investment_goals` (retirement, wealth growth, income, preservation) | task-specific |
| `risk_tolerance` (conservative, moderate, aggressive) | task-specific |
| `constraints` (ethical/sector, currency) | task-specific |
| `cultural_constraints` (religious rules, family obligations) | task-specific |

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-browser-use` |
| Environment | `docker` (`network_mode = "public"`) |
| Persona | `persona/datasets/bench-dev-sample/persona_0042.yaml` |
| API key | `ANTHROPIC_API_KEY` or `LLM_API_KEY` |

```bash
uv run harbor run \
  -a persona-browser-use \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/web-portfoliovisualizer_backtest-allocation \
  --env-file .env
```

Oracle (reference submission; best-effort page reachability, needs outbound
network):

```bash
uv run harbor run -p application/tasks/web-portfoliovisualizer_backtest-allocation -a oracle
```

## Notes

- The verifier checks the **submission schema** (allocation sums to 100, valid
  goal/risk/alignment enums, numeric results, a flagged-concerns list, and a
  written reason) — not semantic match to live figures, which change over time.
  On success it also emits `structured_output.json` with `task_outcome`,
  `web_artifact`, `decision`, `risk_disclosure`, and `user_feedback` contexts,
  which `reporting.json` `contextRules` aggregate across a persona batch.
- Portfolio Visualizer is a heavy JS form. A real browser loads it fine
  (verified: Chromium with a normal user-agent gets HTTP 200 and the full
  allocation form — Time Period, Start Year, Initial Amount, and the asset-class
  rows), but a plain HTTP client (e.g. `curl`) is rejected with HTTP 403. Prefer
  the `persona-browser-use` or CUA loops over terminal scraping; the oracle emits
  a reference submission and does not depend on scraping live metrics.
- Live asset-class names follow the site's dropdown, e.g. `US Stock Market
  (VTSMX)`, `US Small Cap Value (VISVX)`, `Global ex-US Stock Market (VGTSX)`.
- The instruction tells personas to build the allocation themselves via the
  **Add Asset** control rather than only re-weighting the two default rows, and
  makes clear they *may* add many asset classes or individual tickers/funds.
  This is persona-driven, not enforced (the verifier floor stays at ≥2 classes
  summing to 100), so how diversified each portfolio is becomes a real signal
  that varies across the cohort instead of collapsing to a single 60/40 tweak.
- Batch metrics — risk personalization (does the allocation match the stated
  risk tolerance and goal?) and risk-disclosure quality (did the persona flag
  optimistic CAGR extrapolation, short windows, or intolerable drawdowns?) —
  are defined as `contextRules` in [`reporting.json`](reporting.json), plus
  goal-alignment and satisfaction summaries.
- Persona sampling cohort (working-age investors, stratified by risk tolerance)
  is declared in [`persona_strategy.json`](persona_strategy.json).
