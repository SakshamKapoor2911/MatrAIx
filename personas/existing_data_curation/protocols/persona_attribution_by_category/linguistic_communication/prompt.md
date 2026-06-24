You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Linguistic: Communication  (37 dimensions)

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
- tone_expected — Expected tone — Tone they want back. — [Concise | Detailed | Warm / empathetic | Formal | Playful | Blunt]
- ind_telecommunications — Industry: Telecommunications — Work experience in telecommunications. — [Veteran | Experienced | Some exposure | None]
- cog_verbosity — Verbosity — Verbosity. — [Terse | Concise | Balanced | Wordy | Rambling]
- cog_formality — Formality — Formality. — [Very formal | Formal | Neutral | Casual | Slangy]
- cog_directness — Directness — Directness. — [Blunt | Direct | Balanced | Indirect | Evasive]
- cog_humor — Humor style — Humor style. — [Dry | Sarcastic | Playful | Wholesome | Serious]
- cog_detail_orientation — Detail orientation — Detail orientation. — [Very high | High | Moderate | Low | None]
- cog_abstraction — Abstract vs concrete — Abstract vs concrete. — [Highly abstract | Abstract | Balanced | Concrete | Very concrete]
- cog_optimism — Optimism — Optimism. — [Very high | High | Moderate | Low | None]
- cog_patience — Patience — Patience. — [Very high | High | Moderate | Low | None]
- cog_curiosity — Curiosity — Curiosity. — [Very high | High | Moderate | Low | None]
- cog_skepticism — Skepticism — Skepticism. — [Very high | High | Moderate | Low | None]
- cog_open_mindedness — Open-mindedness — Open-mindedness. — [Very high | High | Moderate | Low | None]
- cog_assertiveness — Assertiveness — Assertiveness. — [Very high | High | Moderate | Low | None]
- cog_emotional_expressiveness — Emotional expressiveness — Emotional expressiveness. — [Very high | High | Moderate | Low | None]
- cog_conflict_approach — Conflict approach — Conflict approach. — [Confronting | Collaborative | Compromising | Avoidant | Accommodating]
- cog_feedback_receptiveness — Feedback receptiveness — Feedback receptiveness. — [Very high | High | Moderate | Low | None]
- cog_ambiguity_tolerance — Ambiguity tolerance — Ambiguity tolerance. — [Very high | High | Moderate | Low | None]
- cog_perfectionism — Perfectionism — Perfectionism. — [Very high | High | Moderate | Low | None]
- cog_procrastination — Procrastination tendency — Procrastination tendency. — [Very high | High | Moderate | Low | None]
- cog_multitasking — Multitasking — Multitasking. — [Heavy multitasker | Some | Prefers single-task | Strict monotasker]
- cog_attention_span — Attention span — Attention span. — [Very long | Long | Average | Short | Very short]
- cog_learning_pace — Learning pace — Learning pace. — [Very fast | Fast | Average | Deliberate | Slow]
- cog_question_asking — Question-asking — Question-asking. — [Asks constantly | Asks often | Sometimes | Rarely asks]
- cog_decision_speed — Decision speed — Decision speed. — [Snap decisions | Quick | Balanced | Deliberate | Agonizes]
- cog_confidence_calibration — Confidence calibration — Confidence calibration. — [Overconfident | Confident | Well-calibrated | Cautious | Underconfident]
- cog_numeracy_comfort — Numeracy comfort — Numeracy comfort. — [Very high | High | Moderate | Low | None]
- cog_reading_vs_watching — Reading vs watching — Reading vs watching. — [Strongly prefers reading | Prefers reading | No preference | Prefers video | Strongly prefers video]
- cog_visual_vs_verbal — Visual vs verbal thinking — Visual vs verbal thinking. — [Strongly visual | Visual | Mixed | Verbal | Strongly verbal]
- cog_big_picture_vs_detail — Big-picture vs detail — Big-picture vs detail. — [Big-picture only | Big-picture | Both | Detail | Detail-obsessed]
- cog_risk_framing — Risk framing — Risk framing. — [Opportunity-focused | Balanced | Threat-focused]
- cog_empathy_expression — Empathy expression — Empathy expression. — [Very high | High | Moderate | Low | None]
- cog_storytelling — Storytelling tendency — Storytelling tendency. — [Very high | High | Moderate | Low | None]
- cog_precision_of_language — Precision of language — Precision of language. — [Very precise | Precise | Average | Loose | Vague]
- cog_use_of_jargon — Use of jargon — Use of jargon. — [Heavy | Moderate | Light | Avoids jargon]
- cog_emoji_use — Emoji / emoticon use — Emoji / emoticon use. — [Heavy | Moderate | Rare | Never]
- cog_politeness — Politeness — Politeness. — [Very polite | Polite | Neutral | Brusque | Rude]

INPUT:

{{input_json}}
