# Nike Air Max Dn Dynamic Air Purchase Survey

You are the assigned persona. Read the context below and answer every question as that person would.

Harbor runs this survey via **json_survey** (one-shot JSON completion). Your answers are saved to `/app/output/survey_result.json`.

---

## Context

Survey reactions to the Nike Air Max Dn's Dynamic Air feature, a dual-chamber, four-tubed Air unit designed for smoother transition, comfort, and bounce.

---

## Survey questions

Use exact `questionId` values and valid `value` strings from the instrument JSON schema.
Every answer needs a short **rationale** in the persona's voice and a **confidence** between 0 and 1.

### dynamic_air_appeal

The Dynamic Air cushioning feature would make me more interested in trying the Nike Air Max Dn.

*Construct: retail_product_feature_appeal*

**Type:** Likert scale — set `value` to an integer **1**–**5**.

### comfort_price_tolerance

I would pay more for sneakers if the cushioning technology felt noticeably more comfortable during everyday walking.

*Construct: comfort_feature_price_tolerance*

**Type:** Likert scale — set `value` to an integer **1**–**5**.

### purchase_driver

What would most affect your decision to buy the Air Max Dn?

*Construct: sneaker_purchase_driver*

**Type:** Single choice — set `value` to one **choice_id**:
- `comfort`
- `style`
- `price`
- `brand_loyalty`
- `durability`

### proof_requirement

What would Nike need to show or prove for you to believe the Dynamic Air feature is worth it?

*Construct: retail_product_proof_requirement*

**Type:** Free text — set `value` to a short string in the persona's voice.

---

## Output artifact

Save to `/app/output/survey_result.json`:

```json
{
  "instrument": {
    "id": "commerce_nike_air_max_dn_dynamic_air_v1",
    "title": "Nike Air Max Dn Dynamic Air Purchase Survey"
  },
  "answers": [
    {
      "questionId": "dynamic_air_appeal",
      "value": "<answer>",
      "rationale": "Brief persona-grounded reason.",
      "confidence": 0.85
    }
  ],
  "trajectory": []
}
```

- Include one entry in `answers` for each question you answer.
- The runtime fills `trajectory` automatically if you leave it empty.
