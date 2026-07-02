# Product Attitudes

You are the assigned persona. Read the context below and answer every question as that person would.

Harbor runs this survey via **json_survey** (one-shot JSON completion). Your answers are saved to `/app/output/survey_result.json`.

---

## Context

A short product-concept survey completed directly by the simulated persona respondent.

---

## Survey questions

Use exact `questionId` values and valid `value` strings from the instrument JSON schema.
Every answer needs a short **rationale** in the persona's voice and a **confidence** between 0 and 1.

### concept_fit

This product would fit my current needs.

*Construct: product_need_fit*

**Type:** Likert scale — set `value` to an integer **1**–**5**.

### preference_fit

This product matches my personal preferences.

*Construct: personal_preference_fit*

**Type:** Likert scale — set `value` to an integer **1**–**5**.

### adoption_barrier

What would be your biggest barrier to using this product?

*Construct: adoption_barrier*

**Type:** Single choice — set `value` to one **choice_id**:
- `price`
- `privacy`
- `complexity`
- `trust`
- `no clear need`

### purchase_likelihood

How likely would you be to try or purchase this product?

*Construct: purchase_likelihood*

**Type:** Single choice — set `value` to one **choice_id**:
- `very unlikely`
- `unlikely`
- `neutral`
- `likely`
- `very likely`

### open_feedback

Briefly explain what most influenced your reaction.

*Construct: open_feedback*

**Type:** Free text — set `value` to a short string in the persona's voice.

---

## Output artifact

Save to `/app/output/survey_result.json`:

```json
{
  "instrument": {
    "id": "product_attitudes_v1",
    "title": "Product Attitudes"
  },
  "answers": [
    {
      "questionId": "concept_fit",
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
