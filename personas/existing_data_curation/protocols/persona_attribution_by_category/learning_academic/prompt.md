You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Learning: Academic  (38 dimensions)

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
- highest_education — Highest education — Highest level of formal education completed. — [No formal | Primary | Secondary | Vocational / cert | Bachelor's | Master's | Doctorate | Postdoc]
- academic_field — Academic field — Field of formal study. — [STEM | Medicine | Law | Business | Humanities | Social science | Arts | Interdisciplinary]
- institution_tier — Institution tier — Type/prestige of the educating institution. — [Top-tier research | Mid-tier university | Community college | Online / bootcamp | Self-taught | Not applicable]
- fam_special_education — Familiarity: Special education — How well the persona knows Special education. — [Expert | Proficient | Familiar | Aware | None]
- ind_education — Industry: Education — Work experience in education. — [Veteran | Experienced | Some exposure | None]
- acad_algebra — Subject: Algebra — Interest in algebra. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_geometry — Subject: Geometry — Interest in geometry. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_calculus — Subject: Calculus — Interest in calculus. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_statistics — Subject: Statistics — Interest in statistics. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_physics — Subject: Physics — Interest in physics. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_chemistry — Subject: Chemistry — Interest in chemistry. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_biology — Subject: Biology — Interest in biology. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_earth_science — Subject: Earth science — Interest in earth science. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_computer_science — Subject: Computer science — Interest in computer science. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_economics — Subject: Economics — Interest in economics. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_psychology — Subject: Psychology — Interest in psychology. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_sociology — Subject: Sociology — Interest in sociology. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_world_history — Subject: World history — Interest in world history. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_geography — Subject: Geography — Interest in geography. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_civics — Subject: Civics — Interest in civics. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_literature — Subject: Literature — Interest in literature. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_creative_writing — Subject: Creative writing — Interest in creative writing. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_foreign_languages — Subject: Foreign languages — Interest in foreign languages. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_philosophy — Subject: Philosophy — Interest in philosophy. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_visual_art — Subject: Visual art — Interest in visual art. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_music — Subject: Music — Interest in music. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_drama — Subject: Drama — Interest in drama. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_physical_education — Subject: Physical education — Interest in physical education. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_health_science — Subject: Health science — Interest in health science. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_business_studies — Subject: Business studies — Interest in business studies. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_environmental_science — Subject: Environmental science — Interest in environmental science. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_logic — Subject: Logic — Interest in logic. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_astronomy — Subject: Astronomy — Interest in astronomy. — [Passionate | Interested | Neutral | Indifferent | Averse]
- acad_anthropology — Subject: Anthropology — Interest in anthropology. — [Passionate | Interested | Neutral | Indifferent | Averse]
- wiki_field_of_work — Field of Work — Academic or professional discipline. — [Physics | Medicine | Literature | Politics | Law | Engineering | Business | Arts | Sports | Religion]
- wiki_education_level — Educational Attainment — Highest level of formal education achieved. — [No formal education | Primary | Secondary | Bachelor's degree | Master's degree | Doctorate | Postdoctoral]
- nemotron_education_level — Education Level — Highest level of formal education completed. — [9th_12th_no_diploma | associates | bachelors | graduate | high_school | less_than_9th | some_college]
- nemotron_bachelors_field — Bachelor's Degree Field — Field of study for bachelor's degree (if applicable). — [arts_humanities | business | education | stem | stem_related]

INPUT:

{{input_json}}
