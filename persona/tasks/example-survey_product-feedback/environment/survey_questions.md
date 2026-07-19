# ClearQueue — pricing & fit survey

Read `product_brief.md` first, then answer below.

Pick one option per question (`choice_id`). Copy the id into your JSON — do not paraphrase the label.

Each question has **four spending-posture options** (plus `q0_not_interested` to decline the rest). Options are written so **one choice per question** best matches each spending posture (~90% sufficiency/necessity). **Trying the free tier is normal for everyone** — pick the option that matches your **default toward paying**, not whether you would try free.

| Question | Isolates |
|----------|----------|
| q0 | Default pay intent after trying free |
| q1 | Receptivity to Plus vs Pro |
| q2 | Prepay / lock-in willingness |
| q3 | Reaction to a $1 promo |
| q4 | Pay vs hunt free when switching |
| q5 | Pay to remove ads? |
| q6 | Overall price stance |

## q0 — After trying the free version, your realistic plan is…

| choice_id | Option |
|-----------|--------|
| `q0_use_free_wont_pay` | Keep using free — I avoid paying when I can and would only upgrade if I absolutely have to |
| `q0_pay_when_roi_clear` | Start free, but I'll upgrade once I can prove the time savings are worth the price |
| `q0_subscribe_paid_launch` | I'd subscribe to Plus (or better) at launch — I want the full experience from day one |
| `q0_free_never_decide_tier` | I'd use free and probably never think about tiers |
| `q0_not_interested` | Skip — not for me |

## If you are **not** going to answer the rest

Set `"participation": "declined"`. Include **q0 only** in `responses`, plus `overall_interest` and `would_try_beta`.

## If you **are** going to answer the rest

Set `"participation": "continued"`. Include **q0–q6** in `responses`, plus `overall_interest` and `would_try_beta`.

---

## q1 — Plus vs Pro ($5 more per month)…

| choice_id | Option |
|-----------|--------|
| `q1_reject_both_tiers` | I wouldn't pay for either — paid tiers aren't in my budget |
| `q1_plus_after_sustained_use` | Plus only after sustained use proves it; Pro isn't worth $5 more |
| `q1_happy_plus_or_pro` | I'd happily take Plus or Pro — the extra $5 for Pro is fine |
| `q1_wont_compare_tiers` | I wouldn't spend effort comparing Plus vs Pro |

## q2 — Annual vs monthly billing…

| choice_id | Option |
|-----------|--------|
| `q2_monthly_cancel_anytime` | Monthly only — I refuse to prepay; I need to cancel the instant it's not worth it |
| `q2_annual_after_long_use` | I'd prepay annually only after a long trial proves steady, ongoing value |
| `q2_prepay_annual_plus` | I'd prepay annually on Plus upfront — no need to wait and see |
| `q2_billing_no_preference` | Monthly vs annual doesn't matter to me |

## q3 — A limited $1 first-month Plus promo…

| choice_id | Option |
|-----------|--------|
| `q3_skip_even_one_dollar` | I'd skip it — not worth $1 or the signup hassle; I'll stay on free |
| `q3_one_dollar_try_cancel` | I'd try at $1 and cancel unless value is obvious within the month |
| `q3_grab_dollar_promo` | I'd grab the $1 Plus month right away |
| `q3_ignore_promo` | I'd ignore the promo unless I was already planning to upgrade |

## q4 — A friend uses a paid organizer app…

| choice_id | Option |
|-----------|--------|
| `q4_seek_free_alternative` | I'd look for a free alternative first, even if the paid app is good |
| `q4_compare_pay_if_wins` | I'd compare a few options and pay only if one clearly beats staying free |
| `q4_pay_best_no_hunt` | I'd pay for the best app without hunting for a free version first |
| `q4_switch_only_effortless` | I wouldn't switch unless it was handed to me ready to go |

## q5 — Ads on free vs paying to remove them…

| choice_id | Option |
|-----------|--------|
| `q5_ads_not_worth_paying` | Ads are annoying, but not worth paying to remove — free is fine for my budget |
| `q5_ads_pay_if_plus_useful` | Ads bother me, but I'd pay only if Plus is clearly useful beyond ad-free |
| `q5_pay_primarily_adfree` | Removing ads alone is worth paying Plus or Pro |
| `q5_ads_irrelevant_to_tier` | Ads wouldn't factor into whether I upgrade — I'd ignore that tradeoff |

## q6 — Overall, ClearQueue's pricing feels…

| choice_id | Option |
|-----------|--------|
| `q6_too_expensive_stay_free` | Too expensive for what I'd use — I'd leave before paying |
| `q6_fair_if_use_justifies` | Fair only if my daily use clearly justifies the subscription |
| `q6_premium_price_ok` | Reasonable — I'd pay for premium convenience |
| `q6_pricing_unnoticed` | I don't really notice or care about the pricing |
