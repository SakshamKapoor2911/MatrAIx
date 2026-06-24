You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Interests: Food  (35 dimensions)

Return ONLY JSON with this shape (no markdown, no commentary):

{
  "fields": [
    {
      "field_id": "<one id from the DIMENSIONS list below>",
      "value": "<exactly one allowed value for that id, copied verbatim, or null>",
      "confidence": 0.0,
      "evidence": "<short quote copied from profile_text>",
      "assignment_type": "direct"
    }
  ],
  "reported_model": null,
  "model_source": "user_declared",
  "model_confidence": "user_declared"
}

Allowed assignment_type values:
- direct: explicitly stated in the text.
- structured_claim: derived from structured facts in the input.
- summary_inference: reasonable inference from the profile summary.
- unsupported: not supported by the input.

Rules:
- Emit exactly one object per dimension listed below, in the same order.
- value MUST be exactly one of that dimension's allowed values (copy it verbatim), OR null.
- If the profile does not support a dimension, set value to null and assignment_type to "unsupported".
- Every non-null value MUST include a short evidence quote copied from profile_text.
- Do not infer private, sensitive, or psychological traits unless directly stated; when unsure, prefer null/unsupported.
- Return valid JSON only, with no markdown.

DIMENSIONS (field_id — label — description — allowed values):
- cuis_italian — Cuisine: Italian — Taste for Italian cuisine. — [Love | Like | Neutral | Avoid]
- cuis_french — Cuisine: French — Taste for French cuisine. — [Love | Like | Neutral | Avoid]
- cuis_spanish — Cuisine: Spanish — Taste for Spanish cuisine. — [Love | Like | Neutral | Avoid]
- cuis_greek — Cuisine: Greek — Taste for Greek cuisine. — [Love | Like | Neutral | Avoid]
- cuis_mexican — Cuisine: Mexican — Taste for Mexican cuisine. — [Love | Like | Neutral | Avoid]
- cuis_peruvian — Cuisine: Peruvian — Taste for Peruvian cuisine. — [Love | Like | Neutral | Avoid]
- cuis_brazilian — Cuisine: Brazilian — Taste for Brazilian cuisine. — [Love | Like | Neutral | Avoid]
- cuis_american_bbq — Cuisine: American BBQ — Taste for American BBQ cuisine. — [Love | Like | Neutral | Avoid]
- cuis_southern_soul_food — Cuisine: Southern soul food — Taste for Southern soul food cuisine. — [Love | Like | Neutral | Avoid]
- cuis_cajun — Cuisine: Cajun — Taste for Cajun cuisine. — [Love | Like | Neutral | Avoid]
- cuis_chinese — Cuisine: Chinese — Taste for Chinese cuisine. — [Love | Like | Neutral | Avoid]
- cuis_sichuan — Cuisine: Sichuan — Taste for Sichuan cuisine. — [Love | Like | Neutral | Avoid]
- cuis_cantonese — Cuisine: Cantonese — Taste for Cantonese cuisine. — [Love | Like | Neutral | Avoid]
- cuis_japanese — Cuisine: Japanese — Taste for Japanese cuisine. — [Love | Like | Neutral | Avoid]
- cuis_korean — Cuisine: Korean — Taste for Korean cuisine. — [Love | Like | Neutral | Avoid]
- cuis_thai — Cuisine: Thai — Taste for Thai cuisine. — [Love | Like | Neutral | Avoid]
- cuis_vietnamese — Cuisine: Vietnamese — Taste for Vietnamese cuisine. — [Love | Like | Neutral | Avoid]
- cuis_indian — Cuisine: Indian — Taste for Indian cuisine. — [Love | Like | Neutral | Avoid]
- cuis_pakistani — Cuisine: Pakistani — Taste for Pakistani cuisine. — [Love | Like | Neutral | Avoid]
- cuis_middle_eastern — Cuisine: Middle Eastern — Taste for Middle Eastern cuisine. — [Love | Like | Neutral | Avoid]
- cuis_lebanese — Cuisine: Lebanese — Taste for Lebanese cuisine. — [Love | Like | Neutral | Avoid]
- cuis_turkish — Cuisine: Turkish — Taste for Turkish cuisine. — [Love | Like | Neutral | Avoid]
- cuis_moroccan — Cuisine: Moroccan — Taste for Moroccan cuisine. — [Love | Like | Neutral | Avoid]
- cuis_ethiopian — Cuisine: Ethiopian — Taste for Ethiopian cuisine. — [Love | Like | Neutral | Avoid]
- cuis_nigerian — Cuisine: Nigerian — Taste for Nigerian cuisine. — [Love | Like | Neutral | Avoid]
- cuis_caribbean — Cuisine: Caribbean — Taste for Caribbean cuisine. — [Love | Like | Neutral | Avoid]
- cuis_german — Cuisine: German — Taste for German cuisine. — [Love | Like | Neutral | Avoid]
- cuis_scandinavian — Cuisine: Scandinavian — Taste for Scandinavian cuisine. — [Love | Like | Neutral | Avoid]
- cuis_russian — Cuisine: Russian — Taste for Russian cuisine. — [Love | Like | Neutral | Avoid]
- cuis_spanish_tapas — Cuisine: Spanish tapas — Taste for Spanish tapas cuisine. — [Love | Like | Neutral | Avoid]
- cuis_sushi — Cuisine: Sushi — Taste for Sushi cuisine. — [Love | Like | Neutral | Avoid]
- cuis_ramen — Cuisine: Ramen — Taste for Ramen cuisine. — [Love | Like | Neutral | Avoid]
- cuis_vegan — Cuisine: Vegan — Taste for Vegan cuisine. — [Love | Like | Neutral | Avoid]
- cuis_vegetarian — Cuisine: Vegetarian — Taste for Vegetarian cuisine. — [Love | Like | Neutral | Avoid]
- cuis_seafood — Cuisine: Seafood — Taste for Seafood cuisine. — [Love | Like | Neutral | Avoid]

INPUT:

{{input_json}}
