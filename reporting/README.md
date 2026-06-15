# MatrAIx Reporting

Post-batch analysis for persona simulation jobs. Reads Harbor job/trial outputs and produces aggregated reports (by persona, task, interaction form).

## Status

**Placeholder** — not implemented yet.

## Planned inputs

- `jobs/<job_id>/` — Harbor job results (`result.json`, trial dirs)
- `<trial>/persona_meta.json` — written by persona agents at trial start
- `<trial>/logs/verifier/reward.json` — rewardkit / verifier scores

## Planned outputs

- Persona × task metric tables (CSV / JSON)
- Distribution summaries (not single pass/fail rates)
- Optional HTML report for team review

## Planned CLI (future)

```bash
matraix-report --job-dir jobs/<job_id> --output reports/run-001/
```

## Related Harbor modules

- `harbor metrics/` — job-level mean/max aggregation (keep; reporting goes deeper)
- `harbor analyze/` — LLM qualitative trajectory review (complementary)
- `harbor view` — per-trial inspection

## See also

- [MatrAIx documentation](../docs/README.md)
