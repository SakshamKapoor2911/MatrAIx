# Bookshop choice

Read `input/context.md` for scenario and application background.

Save your choice to `/app/output/book_interest.json`:

```json
{
  "decision_subject_id": "<stable slug or site id for the chosen book>",
  "decision_subject_label": "<book title exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "reason": "<why this book matched you>",
  "task_price_text": "<price exactly as shown, e.g. £51.77>"
}
```

Requirements:

- `decision_subject_id` can be a simple slug you derive from the book title if
  the page does not expose a cleaner id.
- `decision_outcome` should reflect your realistic stance after browsing. For
  this task, `selected` or `considered` will usually make the most sense.
- Keep `reason` specific to the selected book and your persona's preferences.
