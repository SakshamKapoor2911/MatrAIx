# Sample batch reports

Illustrative Playground batch-reporting output for this task, checked in so
reviewers can see the aggregation → PDF pipeline without running the job.

- `live-run-batch-report.pdf` — batch report from a 2-persona live run
  (personas 0069 risk-averse, 0129 risk-tolerant) on Bedrock Claude Sonnet 4.5.
  Both agents drove the live Portfolio Visualizer site, built distinct
  allocations (35/20/40/5 vs 60/20/15/5 equity/bond splits), read the results,
  and reached opposite `satisfied` verdicts; rendered from the job's
  `aggregation.json` after applying this task's `reporting.json` `contextRules`.
- `cua-diversified-allocation-batch-report.pdf` — live CUA run
  (`persona-computer-1`, persona 0042, Bedrock Claude Sonnet 4.5) after the
  instruction was updated to prompt personas to build the allocation via
  **Add Asset** rather than only re-weighting the defaults. The persona built a
  **6-asset** portfolio (US + ex-US equity, bonds, REIT, gold, emerging markets),
  read the live metrics, and returned `satisfied: false` with six flagged
  concerns — demonstrating the richer, diversified submissions the change
  unlocks. Reward 1.0. Exported from the **Playground UI** batch-report view
  (the branded front-matter + rendered aggregation report, `Download PDF`),
  which is more readable than the server-side `report.pdf`.

These are **sample artifacts, not part of the task contract** — safe to drop
from the PR if the repo prefers not to track generated reports. Regenerate with:

```bash
# Live browser-use over Bedrock (or set ANTHROPIC_API_KEY and use an anthropic/ model):
export AWS_BEARER_TOKEN_BEDROCK=...   # or ANTHROPIC_API_KEY=...
export AWS_REGION=us-east-1
uv run harbor run \
  -a persona-browser-use \
  -m bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/web-portfoliovisualizer_backtest-allocation
# then open the job in the Playground Runs view and click "Download PDF"
```
