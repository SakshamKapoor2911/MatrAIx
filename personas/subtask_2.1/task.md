# Subtask 2.1 — Collect open-source persona datasets

Skeleton to collect persona datasets and normalize them into the MatrAIx schema
(`../dimensions.json`). Plumbing works; field-to-dimension normalization is TBD.

## Files

- `catalog.json` — list of datasets, 5 fields each: `id, name, link, description, raw_path`
- `fetch.py` — download a dataset (by HF link) into `raw_path`
- `normalize.py` — wrap each raw record into a MatrAIx envelope → `normalized/<id>.jsonl`

## Add a dataset

1. Add an entry to `catalog.json` (unique `id`).
2. `python normalize.py --source <id> --fetch` (download + normalize).

For non-HF links or datasets needing a config, download to `raw_path` manually first.

## TODO

- [ ] Decide normalization depth (fill `dimensions` / `narrative`, now empty).
- [ ] Per-source field → dimension mapping, validated against `../dimensions.json`.
- [ ] License + DATASHEET per dataset (see `../../Contribution.md`).
- [ ] Extend `fetch.py` for HF configs (e.g. Persona Hub) and non-HF sources.
