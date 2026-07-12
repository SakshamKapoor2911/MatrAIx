# Purchase-intent survey — a product you were considering just changed

You are a shopper who had a specific product in mind. One thing about it has
changed. Answer a short purchase-intent survey as yourself — not as a generic
shopper.

## Your case

`/app/input/cases.jsonl` holds many product cases, one JSON object per line,
each with a `case_id`. Complete the case whose `case_id` equals the `CASE_ID`
environment variable; if `CASE_ID` is unset, use `case_id` 1.

Each case object has the product (`product_name`, `brand`, `original_price`,
`attributes`, `rating`, …) and a `change` block describing the one thing that
changed — its `type` (`price` or `attribute`), which `attribute`, and the value
`before` and `after`. Everything else about the product is unchanged.

`/app/input/survey.md` lists the six questions and their exact answer codes.

Read your case and the survey. Before answering, briefly ground yourself in who
you are: given your background and spending priorities, how much would this
specific change actually matter to you? You don't need an explicit budget stated
in your background to have a clear, grounded opinion — reason from the life you
actually lead, and weigh the real details of your case rather than reacting to
"a product changed" in the abstract.

## Output

Save a single valid JSON object to `/app/output/purchase_decision.json`.

The object must have exactly these six fields. The block below shows the JSON
shape only — do not copy any wording or values from it; every field must
reflect your own judgment about this specific product and change:

```json
{
  "purchase_intent": "<one of the 5 allowed values>",
  "price_fairness": "<one of the 5 allowed values>",
  "alternative_seeking": "<yes or no>",
  "purchase_timing": "<one of the 3 allowed values>",
  "necessity_level": "<one of the 3 allowed values>",
  "reasoning": "<1-3 sentences, in your own words, specific to you and this product>"
}
```

### Allowed values

- **`purchase_intent`** — how likely you are to buy given the change:
  `"definitely_would_buy"`, `"probably_would_buy"`, `"might_or_might_not"`,
  `"probably_would_not"`, `"definitely_would_not"`.
- **`price_fairness`** — how you perceive the price relative to the product's
  value now: `"much_too_high"`, `"somewhat_high"`, `"about_right"`,
  `"good_value"`, `"great_value"`.
- **`alternative_seeking`** — whether you would look for a competing product or
  brand instead because of this change: `"yes"` or `"no"`.
- **`purchase_timing`** — when, if ever, you would buy given the change:
  `"buy_now"`, `"wait_for_sale"`, `"not_planning_to_buy"`.
- **`necessity_level`** — how essential this purchase is to you right now:
  `"essential"`, `"important_but_not_urgent"`, `"nice_to_have"`.
- **`reasoning`** — a non-empty string, 1–3 sentences, in your own voice,
  grounded in your situation and this specific product. No generic filler, and
  do not reuse the wording of the example above.

### Rules

- The JSON must be valid and parseable, a single object (not an array).
- Include exactly the six fields above — no more, no fewer.
- Every value must be one of the allowed values for its field.
