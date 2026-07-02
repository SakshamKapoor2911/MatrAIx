# Robinhood Cortex Digests Survey

You are the assigned persona. Read the context below and answer every question as that person would.

Harbor runs this survey via **json_survey** (one-shot JSON completion). Your answers are saved to `/app/output/survey_result.json`.

---

## Context

Survey reactions to Robinhood Cortex Digests, an AI feature that summarizes recent news, events, market information, and signals for a selected stock or crypto asset.

---

## Survey questions

Use exact `questionId` values and valid `value` strings from the instrument JSON schema.
Every answer needs a short **rationale** in the persona's voice and a **confidence** between 0 and 1.

### market_summary_utility

I would use Robinhood Cortex Digests to quickly understand why a stock or crypto asset may be moving before making my own decision.

*Construct: ai_market_summary_utility*

**Type:** Likert scale — set `value` to an integer **1**–**5**.

### source_transparency

I would trust this feature more if it clearly showed the sources behind each market summary.

*Construct: financial_source_transparency_trust*

**Type:** Likert scale — set `value` to an integer **1**–**5**.

### ai_investing_concern

What would be your biggest concern about using AI-generated investing summaries?

*Construct: ai_investing_adoption_barrier*

**Type:** Single choice — set `value` to one **choice_id**:
- `overreliance_on_ai`
- `unclear_sources`
- `missing_risk_context`
- `too_complex`

### safety_requirement

What would Robinhood need to show you before this feature felt safe to use?

*Construct: financial_ai_safety_requirement*

**Type:** Free text — set `value` to a short string in the persona's voice.

---

## Output artifact

Save to `/app/output/survey_result.json`:

```json
{
  "instrument": {
    "id": "finance_robinhood_cortex_digests_v1",
    "title": "Robinhood Cortex Digests Survey"
  },
  "answers": [
    {
      "questionId": "market_summary_utility",
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
