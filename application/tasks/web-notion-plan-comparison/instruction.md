# Compare Notion workspace plans

## Your situation

You are deciding which Notion workspace plan to use for a realistic personal
or work need. Read the scenario brief in `input/context.md`, then make the
choice as yourself.

## Your goal

Use the live Notion pricing page to compare the four standard workspace plans
and select the **one plan you would most realistically choose**.

## Constraints on your behavior

- Use only information visible on the live Notion pricing page.
- Do not invent an exact team size, compliance requirement, security policy,
  organizational rule, or other need that is not included in the information
  provided about you or on the page.
- If the information provided about you does not include a work or organization
  context, choose for your own individual use.
- Use the standard public plan cards. Do not apply education discounts,
  promotions, or negotiated pricing.
- Do not log in, create an account or workspace, sign up, purchase, request a
  demo, contact sales, contact anyone, or visit a third-party site.

## Interaction requirements

Immediately after the pricing page loads, **click or otherwise activate Pay
monthly at least once**, even if it appears to be selected or the prices
already say “per month.” Do not treat the mere presence of the “Pay monthly”
label as evidence that monthly billing is selected: the page can display that
label while showing annual-billing rates. After activating the control, verify
its selected state or that the rendered plan-card prices update before
recording them. If a text-label click fails, locate and use its interactive
parent or associated control rather than assuming the state is already
correct.

Inspect the summaries for all four plans—Free, Plus, Business, and
Enterprise—and examine relevant parts of the visible feature comparison before
deciding. Compare published monthly prices, intended audiences, included
features, and other visible information when relevant.

Save your choice to `/app/output/notion_plan_comparison.json`:

```json
{
  "decision_subject_id": "<free|plus|business|enterprise>",
  "decision_subject_label": "<Free|Plus|Business|Enterprise>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "basis_secondary": "<optional second value from the same enumeration>",
  "exploration_style": "<compared_multiple|deep_research>",
  "reason": "<why this plan fits your realistic use context and priorities, grounded in the page>",
  "task_billing_mode": "monthly",
  "task_source_url": "https://www.notion.com/pricing",
  "task_price_text": "<selected plan standard monthly price text as shown>",
  "task_target_text": "<selected plan audience description as shown>",
  "task_options_considered": [
    {
      "decision_subject_id": "<free|plus|business|enterprise>",
      "decision_subject_label": "<Free|Plus|Business|Enterprise>",
      "task_price_text": "<standard monthly price text as shown>",
      "task_target_text": "<audience description as shown>",
      "task_relevance_note": "<why this was a plausible or implausible option for you>"
    }
  ]
}
```

## Termination criteria

- `task_options_considered` must contain exactly one entry for each standard
  plan: Free, Plus, Business, and Enterprise.
- The selected plan must appear in `task_options_considered`, with matching
  stable ID, canonical label, price text, and audience description.
- Use the fixed lowercase plan IDs shown in the schema and copy each plan
  heading exactly from its plan summary.
- Keep monthly price and audience text faithful to the rendered live page; do
  not invent metadata.
- Use the standard public plan cards. Do not apply education discounts,
  promotions, or negotiated pricing.
- `basis_secondary` is optional. If included, it must differ from
  `basis_primary`.
- Because comparison is required, use `compared_multiple` or `deep_research`
  for `exploration_style`.
- Keep `reason` specific to your realistic use context, priorities, and visible
  differences among the plans.
- Do not invent an exact team size, compliance requirement, security policy,
  or organizational rule that is not included in the information provided
  about you or on the page.
- Finish after saving the completed JSON file.

## Success judgment

The task is successful when the saved JSON follows the required structure,
records monthly billing, includes one internally consistent entry for each of
the four standard plans, selects one of those entries, and keeps every plan
label, monthly price, and audience description faithful to the live page.
