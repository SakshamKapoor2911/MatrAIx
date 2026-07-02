# Survey Product Feedback

You are the assigned persona. Read the product concept and answer every question below as that person would — using the exact `choice_id` values where noted.

Harbor runs this survey via **json_survey** (one-shot JSON completion). Your answers are saved to `/app/output/survey_result.json`.

---

## Product concept

**Category:** Family productivity / household coordination  
**Stage:** Concept test (not yet launched)

### One-liner

FocusLoop helps busy parents keep school, activities, and shared errands visible in one calm weekly view — without another group chat.

### Problem

Dual-income households juggle school notices, medical appointments, and travel in scattered channels (WeChat, email, paper flyers). Missed deadlines create stress and last-minute scrambling.

### Proposed solution

- **Shared family calendar** with color-coded members (parents + kids)
- **Weekly digest** every Sunday evening: what matters next week
- **Lightweight task handoffs** (“pick up package”, “sign permission slip”) with one-tap accept
- **Optional school email parsing** (beta) to auto-suggest events — user reviews before adding

### Pricing (proposed)

- Free tier: 2 members, manual events only
- Plus ($6.99/mo): up to 6 members, digest, handoffs
- Pro ($11.99/mo): email parsing, shared grocery list

### Target user

Urban professionals aged 28–45 with at least one school-age child, already using digital calendars but frustrated by fragmentation.

---

## Survey questions

Pick one option per question. For single-choice items, set `value` to the **choice_id** (not the label text).

Each question has spending-posture options. **Trying the free tier is normal** — pick the option that matches your **default toward paying**, not whether you would try free.

### q0 — After trying the free version, your realistic plan is…

| choice_id | Option |
|-----------|--------|
| `q0_use_free_wont_pay` | Keep using free — I avoid paying when I can |
| `q0_pay_when_roi_clear` | Start free, but I'll upgrade once ROI is clear |
| `q0_subscribe_paid_launch` | I'd subscribe to Plus (or better) at launch |
| `q0_free_never_decide_tier` | I'd use free and probably never think about tiers |
| `q0_not_interested` | Skip — not for me |

If you choose `q0_not_interested`, you may answer **q0 only** plus overall_interest and would_try_beta.

### q1 — Plus vs Pro ($5 more per month)…

| choice_id | Option |
|-----------|--------|
| `q1_reject_both_tiers` | I wouldn't pay for either |
| `q1_plus_after_sustained_use` | Plus only after sustained use proves it |
| `q1_happy_plus_or_pro` | I'd happily take Plus or Pro |
| `q1_wont_compare_tiers` | I wouldn't spend effort comparing tiers |

### q2 — Annual vs monthly billing…

| choice_id | Option |
|-----------|--------|
| `q2_monthly_cancel_anytime` | Monthly only — refuse to prepay |
| `q2_annual_after_long_use` | Annual only after a long trial |
| `q2_prepay_annual_plus` | I'd prepay annually on Plus upfront |
| `q2_billing_no_preference` | Monthly vs annual doesn't matter |

### q3 — A limited $1 first-month Plus promo…

| choice_id | Option |
|-----------|--------|
| `q3_skip_even_one_dollar` | Skip — not worth $1 or the hassle |
| `q3_one_dollar_try_cancel` | Try at $1 and cancel unless value is obvious |
| `q3_grab_dollar_promo` | Grab the $1 Plus month right away |
| `q3_ignore_promo` | Ignore unless already planning to upgrade |

### q4 — A friend uses a paid organizer app…

| choice_id | Option |
|-----------|--------|
| `q4_seek_free_alternative` | Look for a free alternative first |
| `q4_compare_pay_if_wins` | Compare options and pay only if one clearly wins |
| `q4_pay_best_no_hunt` | Pay for the best app without hunting for free |
| `q4_switch_only_effortless` | Wouldn't switch unless effortless |

### q5 — Ads on free vs paying to remove them…

| choice_id | Option |
|-----------|--------|
| `q5_ads_not_worth_paying` | Ads annoying but not worth paying to remove |
| `q5_ads_pay_if_plus_useful` | Pay only if Plus is useful beyond ad-free |
| `q5_pay_primarily_adfree` | Removing ads alone is worth paying |
| `q5_ads_irrelevant_to_tier` | Ads wouldn't factor into upgrading |

### q6 — Overall, the product's pricing feels…

| choice_id | Option |
|-----------|--------|
| `q6_too_expensive_stay_free` | Too expensive — I'd stay on free |
| `q6_fair_if_use_justifies` | Fair only if daily use justifies it |
| `q6_premium_price_ok` | Reasonable — I'd pay for premium |
| `q6_pricing_unnoticed` | I don't notice or care about pricing |

### overall_interest

Rate **1** (not interested) through **5** (very interested).

### would_try_beta

Answer **`true`** or **`false`**.

---

## Output artifact

Save to `/app/output/survey_result.json`:

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
      "rationale": "Brief persona-grounded reason.",
      "confidence": 0.85
    }
  ],
  "trajectory": []
}
```

- Include one entry in `answers` for each question you answer (`q0`–`q6`, `overall_interest`, `would_try_beta`).
- Use exact `questionId` values and valid `choice_id` strings (or likert 1–5 for `overall_interest`).
- Every answer needs a short **rationale** in the persona's voice.
- The runtime fills `trajectory` automatically if you leave it empty.
