# Choose an Allrecipes recipe

## Your situation

You are deciding what to prepare for an upcoming meal. Read the scenario brief
in `input/context.md`, then make the choice as yourself.

## Your goal

Use the live Allrecipes website to choose the **one recipe you would most
realistically prepare for the upcoming meal**.

## Constraints on your behavior

- Use only information visible on the live Allrecipes site.
- Use dietary or health-related constraints only when they are explicitly part
  of the information provided about you. Do not invent allergies, medical or
  religious restrictions, household needs, or available equipment.
- Do not log in, create an account, save, rate, review, upload a photo, subscribe
  to a newsletter, purchase, share, contact anyone, or visit a third-party site.
- Do not treat the recipe selection as medical or nutritional advice.

## Interaction requirements

Search or browse the catalog, then open and inspect at least **three distinct
recipe-detail pages** before deciding. Compare ingredients, total time,
servings, preparation difficulty, cuisine, familiarity, novelty, and other
information when they are relevant to you.

Save your choice to `/app/output/recipe_choice.json`:

```json
{
  "decision_subject_id": "<numeric recipe ID from the selected Allrecipes URL>",
  "decision_subject_label": "<recipe title exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "basis_secondary": "<optional second value from the same enumeration>",
  "exploration_style": "<compared_multiple|deep_research>",
  "reason": "<why this recipe fits your situation and preferences, grounded in the pages you inspected>",
  "task_recipe_url": "https://www.allrecipes.com/recipe/<numeric-id>/<recipe-slug>/",
  "task_total_time_text": "<total time exactly as shown>",
  "task_servings": "<positive integer servings count>",
  "task_options_considered": [
    {
      "decision_subject_id": "<numeric recipe ID>",
      "decision_subject_label": "<recipe title exactly as shown>",
      "task_recipe_url": "https://www.allrecipes.com/recipe/<numeric-id>/<recipe-slug>/",
      "task_total_time_text": "<total time exactly as shown>",
      "task_servings": "<positive integer servings count>",
      "task_relevance_note": "<why this was a plausible candidate for you>"
    }
  ]
}
```

## Termination criteria

- `task_options_considered` must contain at least three distinct recipes whose
  detail pages you actually opened.
- The selected recipe must appear in `task_options_considered`, with matching
  title, numeric ID, URL, total time, and servings.
- Use the numeric recipe ID from the URL as `decision_subject_id`.
- Keep titles, total-time text, and servings faithful to the live pages; do not
  invent metadata.
- `basis_secondary` is optional. If included, it must differ from
  `basis_primary`.
- Because comparison is required, use `compared_multiple` or `deep_research`
  for `exploration_style`.
- Keep `reason` specific to your situation and preferences and to evidence from
  the selected recipe page.
- Finish after saving the completed JSON file.

## Success judgment

The task is successful when the saved JSON follows the required structure, the
candidate list contains at least three recipe-detail pages you opened, the
selected recipe matches one candidate, and all recorded titles, IDs, URLs,
total-time text, and servings are faithful to the live site.
