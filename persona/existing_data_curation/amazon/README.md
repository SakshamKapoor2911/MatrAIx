# Amazon Existing-Data Workflows

This folder contains Amazon Reviews 2023 downstream workflows imported from
PersonaBench PR #1 and adapted for MatrAIx.

- `extraction/infer_amazon_review_dimensions.py` builds compact review-memory
  profiles and maps them onto `persona/dimensions.json`.
- `extraction/render_amazon_inference_report.py` renders pilot inference JSONL
  files for inspection.
- `evaluation/evaluate_amazon_persona_rating_holdout.py` prepares blind
  temporal-holdout rating targets and scores baselines or persona predictions.
- `evaluation/predict_amazon_persona_holdout_ratings.py` predicts held-out
  ratings from constructed personas.
- `subscription_json_backend.py` routes LLM calls through local subscription
  CLIs (`codex` or `claude`) instead of HTTP API keys.

The expected input history format is the normalized one-user-per-row JSONL
written by `../scripts/export_hf_amazon_user_histories.py`.

## Subscription Model And Effort

Both LLM workflows accept `--llm-backend codex|claude`, `--model`, and
`--llm-effort`. With Claude Code subscriptions, `--model opus` chooses the
model and `--llm-effort` is passed through to `claude --effort`.

Supported Claude effort values are `low`, `medium`, `high`, `xhigh`, and
`max`.

Use `high` for persona-dimension inference:

```bash
python3 persona/existing_data_curation/amazon/extraction/infer_amazon_review_dimensions.py \
  --user-histories "${MATRIX_DATA_ROOT}/amazon_reviews_2023/user_histories.jsonl.gz" \
  --llm-backend claude \
  --model opus \
  --llm-effort high
```

Start large holdout-prediction runs with `medium`, then raise to `high` for
final evaluations or unstable batches:

```bash
python3 persona/existing_data_curation/amazon/evaluation/predict_amazon_persona_holdout_ratings.py \
  --prediction-targets "${MATRIX_DATA_ROOT}/amazon_reviews_2023/rating_holdout/prediction_targets.jsonl" \
  --inference-output "${MATRIX_DATA_ROOT}/amazon_reviews_2023/inferred_dimensions.jsonl" \
  --llm-backend claude \
  --model opus \
  --llm-effort medium
```

Reserve `xhigh` or `max` for small final checks because they are slower and
consume more subscription capacity.
