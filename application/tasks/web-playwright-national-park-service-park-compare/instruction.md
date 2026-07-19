# National Park Service — Park Comparison & Vacation Choice

## Your situation
You are planning a trip to a US National Park (`https://www.nps.gov/`) and want to compare multiple national parks (e.g. Yellowstone, Yosemite, Grand Canyon, Zion) based on activities, weather alerts, and entrance fees.

## Your goal
Browse park pages on NPS.gov, compare features and visitor guidelines across at least 2 parks, and pick the park that best suits your vacation preferences.

## Constraints on your behavior
- Do not attempt to make campsite reservations or buy passes online.
- Base your comparison on public park information pages.

## Interaction requirements
Save your park comparison to `/app/output/park_compare.json` using the following exact JSON schema:

```json
{
  "decision_subject_id": "<park-code-e.g.-yell-yose-grca>",
  "decision_subject_label": "<park name e.g. Yellowstone National Park>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "options_considered_count": 2,
  "comparison_axes": ["activities", "scenery", "accessibility"],
  "reason": "<explanation of why this park was selected over others>",
  "task_rejected_options": "<names of parks compared but not selected>"
}
```

## Termination criteria
- EITHER save `/app/output/park_compare.json` with your selected park and exit,
- OR if no park fits your trip, save with `"decision_outcome": "deferred"` and exit.

## Success judgment
Your submission will be evaluated on:
1. Valid JSON schema structure saved to `/app/output/park_compare.json`.
2. Factual accuracy of `decision_subject_label` and `task_rejected_options`.
3. Clarity and depth of `comparison_axes` and `reason`.

Read `input/context.md` for background. No login required.
Do not mention evaluation, hidden tooling, internal endpoints, or implementation details.
