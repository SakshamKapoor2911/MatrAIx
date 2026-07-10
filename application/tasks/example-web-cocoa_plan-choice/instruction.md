# Plan preference

Read `input/context.md` for scenario and application background.

Save your choice to `/app/output/plan_choice.json`:

```json
{
  "decision_subject_id": "<stable slug or site id for the chosen plan>",
  "decision_subject_label": "<plan name exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "reason": "<why this plan matched you>",
  "task_price_text": "<price text exactly as shown, e.g. $10/month or $0/month>"
}
```

Requirements:

- `decision_subject_id` can be a simple slug you derive from the plan name if
  the page does not expose a cleaner id.
- `basis_primary` should capture the main factor behind your choice.
- Keep `reason` specific to the selected plan and your persona's preferences.

No signup is required.
