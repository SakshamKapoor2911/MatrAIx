# Survey Product Feedback

## Task instruction

Complete the survey using the provided context and structured questionnaire.

Return one JSON object that matches `input/output_schema.md`.

Requirements:

- Answer every required question in `input/questionnaire.yaml`.
- Use exact `questionId` values from the questionnaire.
- For choice questions, use the exact choice ids.
- For likert questions, use an integer within the declared range.
- Keep each `rationale` concise and specific to the selected answer.
- Do not include `trajectory`; the backend/runtime appends it separately.
- Do not mention file paths, runtime artifacts, or platform internals inside the JSON response.

## Context

Pricing and product-fit survey for the FocusLoop family coordination app
concept. Use the choice ids listed for each question.

## Questionnaire

# Survey Product Feedback

Use exact `questionId` and valid choice ids. The platform owns the output schema and standardized trajectory generation.

## q0

Prompt: After trying the free version, your realistic plan is...

- Construct: `default_pay_intent`
- Type: `single_choice`
- Required: `true`

| choice_id | label |
|-----------|-------|
| `q0_use_free_wont_pay` | Keep using free. I avoid paying when I can and would only upgrade if I absolutely have to. |
| `q0_pay_when_roi_clear` | Start free, then upgrade once the time savings clearly justify the price. |
| `q0_subscribe_paid_launch` | Subscribe to Plus or better at launch because I want the full experience immediately. |
| `q0_free_never_decide_tier` | Use free and probably never think much about tiers. |
| `q0_not_interested` | Skip the rest because this product is not for me. |

## q1

Prompt: Plus vs Pro ($5 more per month)...

- Construct: `tier_receptivity`
- Type: `single_choice`
- Required: `true`

| choice_id | label |
|-----------|-------|
| `q1_reject_both_tiers` | I would not pay for either tier because paid plans are outside my budget. |
| `q1_plus_after_sustained_use` | Plus only after sustained use proves value; Pro is not worth the extra $5. |
| `q1_happy_plus_or_pro` | I would happily take Plus or Pro; the extra $5 for Pro feels fine. |
| `q1_wont_compare_tiers` | I would not spend effort comparing Plus vs Pro. |

## q2

Prompt: Annual vs monthly billing...

- Construct: `prepay_willingness`
- Type: `single_choice`
- Required: `true`

| choice_id | label |
|-----------|-------|
| `q2_monthly_cancel_anytime` | Monthly only. I refuse to prepay and want to cancel the moment it stops being worth it. |
| `q2_annual_after_long_use` | I would prepay annually only after a long trial proves steady value. |
| `q2_prepay_annual_plus` | I would prepay annually on Plus upfront without waiting. |
| `q2_billing_no_preference` | Monthly vs annual does not matter to me. |

## q3

Prompt: A limited $1 first-month Plus promo...

- Construct: `promo_reaction`
- Type: `single_choice`
- Required: `true`

| choice_id | label |
|-----------|-------|
| `q3_skip_even_one_dollar` | I would skip it. It is not worth even $1 or the signup hassle. |
| `q3_one_dollar_try_cancel` | I would try it at $1 and cancel unless value becomes obvious within the month. |
| `q3_grab_dollar_promo` | I would grab the $1 Plus month right away. |
| `q3_ignore_promo` | I would ignore the promo unless I was already planning to upgrade. |

## q4

Prompt: A friend uses a paid organizer app...

- Construct: `switch_behavior`
- Type: `single_choice`
- Required: `true`

| choice_id | label |
|-----------|-------|
| `q4_seek_free_alternative` | I would look for a free alternative first, even if the paid app seems good. |
| `q4_compare_pay_if_wins` | I would compare a few options and pay only if one clearly beats staying free. |
| `q4_pay_best_no_hunt` | I would pay for the best app without hunting for a free version first. |
| `q4_switch_only_effortless` | I would not switch unless it was basically handed to me ready to go. |

## q5

Prompt: Ads on free vs paying to remove them...

- Construct: `ads_tradeoff`
- Type: `single_choice`
- Required: `true`

| choice_id | label |
|-----------|-------|
| `q5_ads_not_worth_paying` | Ads are annoying, but not enough to make me pay. |
| `q5_ads_pay_if_plus_useful` | Ads bother me, but I would pay only if Plus is useful beyond ad-free. |
| `q5_pay_primarily_adfree` | Removing ads alone is enough value for me to pay. |
| `q5_ads_irrelevant_to_tier` | Ads would not factor into whether I upgrade. |

## q6

Prompt: Overall, the product's pricing feels...

- Construct: `price_stance`
- Type: `single_choice`
- Required: `true`

| choice_id | label |
|-----------|-------|
| `q6_too_expensive_stay_free` | Too expensive for what I would use; I would leave before paying. |
| `q6_fair_if_use_justifies` | Fair only if my daily use clearly justifies the subscription. |
| `q6_premium_price_ok` | Reasonable. I would pay for premium convenience. |
| `q6_pricing_unnoticed` | I do not really notice or care about the pricing. |

## overall_interest

Prompt: Overall interest in this product.

- Construct: `overall_interest`
- Type: `likert`
- Required: `true`
- Scale: `1`-`5`

Rate with an integer between **1** and **5**.


## would_try_beta

Prompt: Would you try a beta version?

- Construct: `beta_intent`
- Type: `single_choice`
- Required: `true`

| choice_id | label |
|-----------|-------|
| `true` | Yes, I would try the beta. |
| `false` | No, I would not try the beta. |

## Output schema

Write strict JSON to `/app/output/survey_result.json`.

```json
{
  "instrument": {
    "id": "product_feedback_v1",
    "title": "Survey Product Feedback"
  },
  "answers": [
    {
      "questionId": "q0",
      "value": "q0_pay_when_roi_clear",
      "rationale": "Brief answer-specific reason.",
      "confidence": 0.85
    }
  ]
}
```

Rules:

- Use exact `questionId` values from `questionnaire.yaml`.
- For choice questions, `value` must be the exact choice id.
- `overall_interest` uses a 1-5 integer.
- `would_try_beta` uses `"true"` or `"false"`.
- Do not include `trajectory`; the backend/runtime appends the standardized survey trajectory.