You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Demographic: Core  (27 dimensions)

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
- age_bracket — Age bracket — Life-age band of the persona. — [13–17 | 18–24 | 25–34 | 35–44 | 45–54 | 55–64 | 65+]
- region — Region — World region the persona is based in. — [North America | Latin America | Western Europe | Eastern Europe | Sub-Saharan Africa | MENA | South Asia | East Asia | Southeast Asia | Oceania]
- gender_identity — Gender identity — Self-identified gender. — [Woman | Man | Non-binary | Self-described | Prefer not to say]
- urbanicity — Urbanicity — Settlement density of where they live. — [Dense urban | Suburban | Small town | Rural | Nomadic / remote]
- socioeconomic_band — Socioeconomic band — Relative income/wealth band. — [Low income | Lower-middle | Middle | Upper-middle | High income]
- register — Dialect / register — Default speech register. — [Formal / standard | Colloquial | Regional dialect | Code-switching | Technical jargon]
- att_traditional_gender_roles — Attitude: Traditional gender roles — Stance toward traditional gender roles. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- demo_marital_status — Marital status — Marital status. — [Single | In a relationship | Married | Domestic partnership | Separated | Divorced | Widowed]
- demo_children_count — Children — Children. — [None | Expecting | 1 child | 2 children | 3+ children | Adult children]
- demo_household_income — Household income band — Household income band. — [<$25k | $25k–50k | $50k–100k | $100k–200k | $200k+]
- demo_employment_status — Employment status — Employment status. — [Full-time | Part-time | Self-employed | Gig / freelance | Student | Unemployed | Retired | Homemaker]
- demo_housing_status — Housing status — Housing status. — [Own outright | Mortgage | Renting | Living with family | Shared housing | Temporary / transitional]
- demo_generation — Generational cohort — Generational cohort. — [Gen Alpha | Gen Z | Millennial | Gen X | Boomer | Silent]
- demo_religion_affiliation — Religious affiliation — Religious affiliation. — [Christian | Muslim | Hindu | Buddhist | Jewish | Sikh | Folk / traditional | Spiritual but unaffiliated | Atheist / agnostic | None]
- demo_sexual_orientation — Sexual orientation — Sexual orientation. — [Heterosexual | Gay / lesbian | Bisexual | Pansexual | Asexual | Queer | Prefer not to say]
- demo_citizenship_status — Citizenship status — Citizenship status. — [Citizen by birth | Naturalized citizen | Permanent resident | Visa holder | Dual national | Undocumented]
- demo_ethnicity_broad — Ethnic background — Ethnic background. — [White / European | Black / African | Hispanic / Latino | East Asian | South Asian | Southeast Asian | Middle Eastern | Indigenous | Pacific Islander | Multiracial]
- demo_disability_status — Disability status — Disability status. — [No disability | Physical | Sensory | Cognitive | Chronic illness | Multiple | Prefers not to say]
- demo_veteran_status — Veteran status — Veteran status. — [Civilian | Active duty | Reserve / guard | Veteran | Military family]
- demo_birth_order — Birth order — Birth order. — [Only child | Eldest | Middle | Youngest | Twin / multiple]
- demo_home_language — Language at home — Language at home. — [Same as primary | Bilingual home | Heritage language | Mixed languages]
- demo_political_engagement — Political engagement — Political engagement. — [Activist | Engaged voter | Occasional voter | Disengaged | Non-voter]
- demo_parental_status — Parenthood — Parenthood. — [Not a parent | New parent | Parent of minors | Parent of adults | Grandparent | Step / foster parent]
- demo_relationship_length — Relationship length — Relationship length. — [Not in one | Under 1 year | 1–5 years | 5–15 years | 15+ years]
- demo_driver_status — Driving status — Driving status. — [Daily driver | Occasional driver | Licensed, rarely drives | Non-driver | Cannot drive]
- wiki_nationality — Nationality — Primary country or countries of citizenship. — [American | British | French | German | Japanese | Chinese | Indian | Canadian | Australian | Other]
- nemotron_sex — Sex — Biological sex. — [Female | Male]

INPUT:

{{input_json}}
