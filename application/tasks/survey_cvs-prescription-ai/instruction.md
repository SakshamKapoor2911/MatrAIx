# CVS Health App Prescription AI Survey

You are the assigned persona. Read the context below and answer every question as that person would.

Harbor runs this survey via **json_survey** (one-shot JSON completion). Your answers are saved to `/app/output/survey_result.json`.

---

## Context

Survey reactions to the CVS Health app's conversational AI experience for checking medication refills, order status, and related pharmacy tasks.

---

## Survey questions

Use exact `questionId` values and valid `value` strings from the instrument JSON schema.
Every answer needs a short **rationale** in the persona's voice and a **confidence** between 0 and 1.

### pharmacy_convenience

I would use a CVS app chat assistant to check prescription refill status or order status instead of calling the pharmacy.

*Construct: pharmacy_ai_convenience*

**Type:** Likert scale — set `value` to an integer **1**–**5**.

### pharmacy_boundary_trust

I would feel comfortable using this assistant for simple pharmacy tasks, as long as it did not replace pharmacist support for medical questions.

*Construct: pharmacy_ai_boundary_trust*

**Type:** Likert scale — set `value` to an integer **1**–**5**.

### pharmacy_hesitation

What would make you most hesitant to use a pharmacy chat assistant?

*Construct: pharmacy_ai_adoption_barrier*

**Type:** Single choice — set `value` to one **choice_id**:
- `privacy`
- `wrong_medication_information`
- `hard_to_reach_a_human`
- `app_usability`

### wanted_pharmacy_task

What pharmacy task would you most want this assistant to handle for you?

*Construct: pharmacy_ai_use_case*

**Type:** Free text — set `value` to a short string in the persona's voice.

---

## Output artifact

Save to `/app/output/survey_result.json`:

```json
{
  "instrument": {
    "id": "healthcare_cvs_app_prescription_ai_v1",
    "title": "CVS Health App Prescription AI Survey"
  },
  "answers": [
    {
      "questionId": "pharmacy_convenience",
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
