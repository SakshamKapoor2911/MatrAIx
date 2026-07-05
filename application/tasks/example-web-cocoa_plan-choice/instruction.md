# Plan preference

Browse the public pricing page at:

https://www.pythonanywhere.com/pricing/

Imagine you were considering a hosted place for small personal Python projects,
experiments, or a lightweight web app. Compare the plans as yourself and pick
the **one plan** you would most realistically consider.

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

- Read the plan name and price text from the live page; do not invent values.
- `decision_subject_id` can be a simple slug you derive from the plan name if
  the page does not expose a cleaner id.
- `basis_primary` should capture the main factor behind your choice.
- Keep `reason` specific to the selected plan and your persona's preferences.

No signup is required.
