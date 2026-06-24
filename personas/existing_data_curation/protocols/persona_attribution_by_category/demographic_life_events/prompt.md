You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Demographic: Life Events  (25 dimensions)

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
- life_stage — Life stage — Current stage of life. — [Student | Early career | Parent of young kids | Mid-life | Career change | Empty nester | Retirement]
- major_life_events — Major life events — Defining experience shaping their outlook. — [Migration / immigration | Started a business | Health journey | Military service | Caregiving | Bereavement | Major relocation | None notable]
- lifex_childhood_environment — Childhood environment — Childhood environment. — [Stable & secure | Modest but steady | Turbulent | Privileged | Hardship | Frequently uprooted]
- lifex_geographic_mobility — Geographic mobility — Geographic mobility. — [Never left hometown | Moved within region | Moved nationally | Moved internationally | Serial relocator]
- lifex_travel_breadth — Travel breadth — Travel breadth. — [Never left country | A few countries | Well-traveled | Lived abroad | Global nomad]
- lifex_career_path_shape — Career path shape — Career path shape. — [Linear climb | Pivoted once | Multiple pivots | Entrepreneurial | Portfolio / patchwork | Just starting]
- lifex_education_journey — Education journey — Education journey. — [Traditional track | Returned as adult | Largely self-taught | Dropped out | Advanced degrees | Vocational / trade]
- lifex_financial_trajectory — Financial trajectory — Financial trajectory. — [Steady upward | Stable | Volatile | Downward | Rebuilt after setback | Inherited wealth]
- lifex_adversity_level — Adversity faced — Adversity faced. — [Sheltered | Minor setbacks | Significant struggles | Overcame major hardship | Ongoing hardship]
- lifex_immigration_generation — Immigration generation — Immigration generation. — [First-generation immigrant | Second-generation | Third+ generation | Native multi-generational | Returnee / repatriate]
- lifex_military_history — Military history — Military history. — [Never served | Served briefly | Career veteran | Combat veteran | Military family]
- lifex_entrepreneurship_history — Entrepreneurship history — Entrepreneurship history. — [Never considered | Considered it | Side hustle | Founded once | Serial founder | Exited a company]
- lifex_relationship_history — Relationship history — Relationship history. — [Limited | A few relationships | Long-term partnership | Married once | Remarried | Widowed]
- lifex_parenting_journey — Parenting journey — Parenting journey. — [No children | Young children | Teenagers | Grown children | Empty nester | Raising grandchildren]
- lifex_health_journey — Health journey — Health journey. — [No major events | Recovered from illness | Manages chronic condition | Major surgery / injury | Mental health journey | Caregiving for others]
- lifex_loss_experience — Experience of loss — Experience of loss. — [No major loss | Lost a grandparent | Lost a parent | Lost a partner / child | Multiple bereavements]
- lifex_faith_journey — Faith journey — Faith journey. — [Lifelong faith | Converted | Lapsed / left faith | Always secular | Still searching | Returned to faith]
- lifex_cultural_exposure — Cross-cultural exposure — Cross-cultural exposure. — [Monocultural | Some exposure | Multicultural upbringing | Lived across cultures | Third-culture kid]
- lifex_formative_decade — Formative decade — Formative decade. — [1960s–70s | 1980s | 1990s | 2000s | 2010s | 2020s]
- lifex_public_recognition — Public recognition — Public recognition. — [Private life | Locally known | Industry-recognized | Publicly notable | Famous]
- lifex_service_history — Community / service history — Community / service history. — [None | Occasional volunteer | Long-term volunteer | Activist / organizer | Public office]
- lifex_turning_point — Defining turning point — Defining turning point. — [Career break | Near-miss / accident | Spiritual awakening | Reinvention | Mentor encounter | No single one]
- lifex_languages_lifetime — Languages learned over life — Languages learned over life. — [One | Two | Three | Four+ | Polyglot]
- lifex_hometown_tie — Tie to hometown — Tie to hometown. — [Still there | Visits often | Occasional return | Rarely returns | No connection]
- wiki_birth_date — Birth Date — Specific date a person was born; enables age calculation and historical context. — [1800s | 1900-1920 | 1920-1940 | 1940-1960 | 1960-1980 | 1980-2000 | 2000+]

INPUT:

{{input_json}}
