You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Linguistic: Language  (53 dimensions)

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
- primary_language — Primary language — First / dominant language. — [English | Mandarin | Spanish | Hindi | Arabic | French | Portuguese | Bengali | Russian | Japanese | German | Swahili]
- english_proficiency — English proficiency — Command of English (the eval lingua franca). — [Native | Fluent (C1–C2) | Intermediate (B1–B2) | Basic (A1–A2) | None]
- multilingualism — Multilingualism — Number of working languages. — [Monolingual | Bilingual | Trilingual+]
- lang_english — Language: English — Spoken proficiency in English. — [Native | Fluent | Conversational | Basic | None]
- lang_mandarin — Language: Mandarin — Spoken proficiency in Mandarin. — [Native | Fluent | Conversational | Basic | None]
- lang_cantonese — Language: Cantonese — Spoken proficiency in Cantonese. — [Native | Fluent | Conversational | Basic | None]
- lang_spanish — Language: Spanish — Spoken proficiency in Spanish. — [Native | Fluent | Conversational | Basic | None]
- lang_hindi — Language: Hindi — Spoken proficiency in Hindi. — [Native | Fluent | Conversational | Basic | None]
- lang_arabic — Language: Arabic — Spoken proficiency in Arabic. — [Native | Fluent | Conversational | Basic | None]
- lang_french — Language: French — Spoken proficiency in French. — [Native | Fluent | Conversational | Basic | None]
- lang_portuguese — Language: Portuguese — Spoken proficiency in Portuguese. — [Native | Fluent | Conversational | Basic | None]
- lang_bengali — Language: Bengali — Spoken proficiency in Bengali. — [Native | Fluent | Conversational | Basic | None]
- lang_russian — Language: Russian — Spoken proficiency in Russian. — [Native | Fluent | Conversational | Basic | None]
- lang_japanese — Language: Japanese — Spoken proficiency in Japanese. — [Native | Fluent | Conversational | Basic | None]
- lang_german — Language: German — Spoken proficiency in German. — [Native | Fluent | Conversational | Basic | None]
- lang_korean — Language: Korean — Spoken proficiency in Korean. — [Native | Fluent | Conversational | Basic | None]
- lang_italian — Language: Italian — Spoken proficiency in Italian. — [Native | Fluent | Conversational | Basic | None]
- lang_turkish — Language: Turkish — Spoken proficiency in Turkish. — [Native | Fluent | Conversational | Basic | None]
- lang_vietnamese — Language: Vietnamese — Spoken proficiency in Vietnamese. — [Native | Fluent | Conversational | Basic | None]
- lang_thai — Language: Thai — Spoken proficiency in Thai. — [Native | Fluent | Conversational | Basic | None]
- lang_indonesian — Language: Indonesian — Spoken proficiency in Indonesian. — [Native | Fluent | Conversational | Basic | None]
- lang_malay — Language: Malay — Spoken proficiency in Malay. — [Native | Fluent | Conversational | Basic | None]
- lang_swahili — Language: Swahili — Spoken proficiency in Swahili. — [Native | Fluent | Conversational | Basic | None]
- lang_dutch — Language: Dutch — Spoken proficiency in Dutch. — [Native | Fluent | Conversational | Basic | None]
- lang_polish — Language: Polish — Spoken proficiency in Polish. — [Native | Fluent | Conversational | Basic | None]
- lang_ukrainian — Language: Ukrainian — Spoken proficiency in Ukrainian. — [Native | Fluent | Conversational | Basic | None]
- lang_persian — Language: Persian — Spoken proficiency in Persian. — [Native | Fluent | Conversational | Basic | None]
- lang_hebrew — Language: Hebrew — Spoken proficiency in Hebrew. — [Native | Fluent | Conversational | Basic | None]
- lang_greek — Language: Greek — Spoken proficiency in Greek. — [Native | Fluent | Conversational | Basic | None]
- lang_czech — Language: Czech — Spoken proficiency in Czech. — [Native | Fluent | Conversational | Basic | None]
- lang_hungarian — Language: Hungarian — Spoken proficiency in Hungarian. — [Native | Fluent | Conversational | Basic | None]
- lang_romanian — Language: Romanian — Spoken proficiency in Romanian. — [Native | Fluent | Conversational | Basic | None]
- lang_swedish — Language: Swedish — Spoken proficiency in Swedish. — [Native | Fluent | Conversational | Basic | None]
- lang_norwegian — Language: Norwegian — Spoken proficiency in Norwegian. — [Native | Fluent | Conversational | Basic | None]
- lang_danish — Language: Danish — Spoken proficiency in Danish. — [Native | Fluent | Conversational | Basic | None]
- lang_finnish — Language: Finnish — Spoken proficiency in Finnish. — [Native | Fluent | Conversational | Basic | None]
- lang_tagalog — Language: Tagalog — Spoken proficiency in Tagalog. — [Native | Fluent | Conversational | Basic | None]
- lang_urdu — Language: Urdu — Spoken proficiency in Urdu. — [Native | Fluent | Conversational | Basic | None]
- lang_tamil — Language: Tamil — Spoken proficiency in Tamil. — [Native | Fluent | Conversational | Basic | None]
- lang_telugu — Language: Telugu — Spoken proficiency in Telugu. — [Native | Fluent | Conversational | Basic | None]
- lang_marathi — Language: Marathi — Spoken proficiency in Marathi. — [Native | Fluent | Conversational | Basic | None]
- lang_punjabi — Language: Punjabi — Spoken proficiency in Punjabi. — [Native | Fluent | Conversational | Basic | None]
- lang_gujarati — Language: Gujarati — Spoken proficiency in Gujarati. — [Native | Fluent | Conversational | Basic | None]
- lang_hausa — Language: Hausa — Spoken proficiency in Hausa. — [Native | Fluent | Conversational | Basic | None]
- lang_yoruba — Language: Yoruba — Spoken proficiency in Yoruba. — [Native | Fluent | Conversational | Basic | None]
- lang_igbo — Language: Igbo — Spoken proficiency in Igbo. — [Native | Fluent | Conversational | Basic | None]
- lang_amharic — Language: Amharic — Spoken proficiency in Amharic. — [Native | Fluent | Conversational | Basic | None]
- lang_zulu — Language: Zulu — Spoken proficiency in Zulu. — [Native | Fluent | Conversational | Basic | None]
- lang_afrikaans — Language: Afrikaans — Spoken proficiency in Afrikaans. — [Native | Fluent | Conversational | Basic | None]
- lang_serbian — Language: Serbian — Spoken proficiency in Serbian. — [Native | Fluent | Conversational | Basic | None]
- lang_croatian — Language: Croatian — Spoken proficiency in Croatian. — [Native | Fluent | Conversational | Basic | None]
- lang_bulgarian — Language: Bulgarian — Spoken proficiency in Bulgarian. — [Native | Fluent | Conversational | Basic | None]
- lang_slovak — Language: Slovak — Spoken proficiency in Slovak. — [Native | Fluent | Conversational | Basic | None]

INPUT:

{{input_json}}
