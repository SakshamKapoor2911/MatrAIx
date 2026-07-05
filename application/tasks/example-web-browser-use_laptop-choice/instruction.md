# Laptop shortlist

Browse the public laptop catalog at:

https://webscraper.io/test-sites/e-commerce/static/computers/laptops

Compare a few options as yourself and pick the **one laptop** you would most
realistically consider.

Save your choice to `/app/output/laptop_choice.json`:

```json
{
  "decision_subject_id": "<stable slug or site id for the chosen laptop>",
  "decision_subject_label": "<product title exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "reason": "<why this laptop matched you>",
  "task_price_text": "<price exactly as shown, e.g. $739.99>"
}
```

Requirements:

- Read the title and price from the live page; do not invent values.
- `decision_subject_id` can be a simple slug you derive from the title if the
  page does not expose a cleaner id.
- `basis_primary` should reflect the main decision axis behind your choice.
- Keep `reason` specific to the selected laptop and your persona's preferences.

No login or purchase is required.
