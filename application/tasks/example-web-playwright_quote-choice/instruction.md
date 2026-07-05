# Quote to save

Browse the public quotes catalog at:

https://quotes.toscrape.com/

Explore at least a few quotes as yourself and pick the **one quote** you would
most want to save, share, or come back to later.

Save your choice to `/app/output/quote_choice.json`:

```json
{
  "decision_subject_id": "<stable slug or site id for the chosen quote>",
  "decision_subject_label": "<quote text exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "reason": "<why this quote matched you>",
  "task_author": "<author name exactly as shown>"
}
```

Requirements:

- Read quote text and author from the live page; do not invent values.
- `decision_subject_id` can be a simple slug you derive from the quote or
  author if the page does not expose a cleaner id.
- `basis_primary` should capture the main reason the quote resonated with you.
- Keep `reason` specific to the chosen quote and your persona's preferences.

No login or sharing action is required.
