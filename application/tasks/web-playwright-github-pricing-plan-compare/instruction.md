# GitHub Pricing — Tier Comparison & Selection

## Your situation
You are evaluating GitHub plans (`https://github.com/pricing`) for a development team. You need to compare available pricing tiers (Free, Team, Enterprise) against team requirements, budget limits, and security feature needs.

## Your goal
Compare GitHub pricing tiers, evaluate their feature differences, and select the single plan that best fits your team's profile.

## Constraints on your behavior
- Do not attempt to sign up, log in, or initiate trial purchases.
- Base your decision on publicly listed pricing tiers and feature matrices on the GitHub Pricing page.

## Interaction requirements
Save your comparison and final plan decision to `/app/output/plan_compare.json` using the following exact JSON schema:

```json
{
  "decision_subject_id": "<free|team|enterprise>",
  "decision_subject_label": "<plan tier name exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "options_considered_count": 3,
  "comparison_axes": ["price", "features"],
  "reason": "<explanation of why this tier won over alternatives>",
  "task_rejected_options": "<brief note of tiers ruled out and why>"
}
```

## Termination criteria
- EITHER save `/app/output/plan_compare.json` with your selected plan tier and exit,
- OR if none of the plans fit your team constraints, save with `"decision_outcome": "deferred"` and exit.

## Success judgment
Your submission will be evaluated on:
1. Valid JSON schema structure saved to `/app/output/plan_compare.json`.
2. Factual accuracy of `decision_subject_label` and `options_considered_count`.
3. Logical alignment of `comparison_axes`, `reason`, and `task_rejected_options`.

Read `input/context.md` for background. No login required.
Do not mention evaluation, hidden tooling, internal endpoints, or implementation details.
