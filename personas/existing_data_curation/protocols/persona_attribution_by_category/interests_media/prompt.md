You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Interests: Media  (81 dimensions)

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
- musg_pop — Music: Pop — Taste for Pop music. — [Love | Like | Neutral | Dislike]
- musg_rock — Music: Rock — Taste for Rock music. — [Love | Like | Neutral | Dislike]
- musg_hip_hop — Music: Hip-hop — Taste for Hip-hop music. — [Love | Like | Neutral | Dislike]
- musg_r_b — Music: R&B — Taste for R&B music. — [Love | Like | Neutral | Dislike]
- musg_jazz — Music: Jazz — Taste for Jazz music. — [Love | Like | Neutral | Dislike]
- musg_blues — Music: Blues — Taste for Blues music. — [Love | Like | Neutral | Dislike]
- musg_classical — Music: Classical — Taste for Classical music. — [Love | Like | Neutral | Dislike]
- musg_opera — Music: Opera — Taste for Opera music. — [Love | Like | Neutral | Dislike]
- musg_country — Music: Country — Taste for Country music. — [Love | Like | Neutral | Dislike]
- musg_folk — Music: Folk — Taste for Folk music. — [Love | Like | Neutral | Dislike]
- musg_reggae — Music: Reggae — Taste for Reggae music. — [Love | Like | Neutral | Dislike]
- musg_reggaeton — Music: Reggaeton — Taste for Reggaeton music. — [Love | Like | Neutral | Dislike]
- musg_electronic — Music: Electronic — Taste for Electronic music. — [Love | Like | Neutral | Dislike]
- musg_house — Music: House — Taste for House music. — [Love | Like | Neutral | Dislike]
- musg_techno — Music: Techno — Taste for Techno music. — [Love | Like | Neutral | Dislike]
- musg_trance — Music: Trance — Taste for Trance music. — [Love | Like | Neutral | Dislike]
- musg_drum_bass — Music: Drum & bass — Taste for Drum & bass music. — [Love | Like | Neutral | Dislike]
- musg_metal — Music: Metal — Taste for Metal music. — [Love | Like | Neutral | Dislike]
- musg_punk — Music: Punk — Taste for Punk music. — [Love | Like | Neutral | Dislike]
- musg_indie — Music: Indie — Taste for Indie music. — [Love | Like | Neutral | Dislike]
- musg_k_pop — Music: K-pop — Taste for K-pop music. — [Love | Like | Neutral | Dislike]
- musg_j_pop — Music: J-pop — Taste for J-pop music. — [Love | Like | Neutral | Dislike]
- musg_latin — Music: Latin — Taste for Latin music. — [Love | Like | Neutral | Dislike]
- musg_afrobeats — Music: Afrobeats — Taste for Afrobeats music. — [Love | Like | Neutral | Dislike]
- musg_gospel — Music: Gospel — Taste for Gospel music. — [Love | Like | Neutral | Dislike]
- musg_soul — Music: Soul — Taste for Soul music. — [Love | Like | Neutral | Dislike]
- musg_funk — Music: Funk — Taste for Funk music. — [Love | Like | Neutral | Dislike]
- musg_disco — Music: Disco — Taste for Disco music. — [Love | Like | Neutral | Dislike]
- musg_ambient — Music: Ambient — Taste for Ambient music. — [Love | Like | Neutral | Dislike]
- musg_lo_fi — Music: Lo-fi — Taste for Lo-fi music. — [Love | Like | Neutral | Dislike]
- musg_bluegrass — Music: Bluegrass — Taste for Bluegrass music. — [Love | Like | Neutral | Dislike]
- musg_ska — Music: Ska — Taste for Ska music. — [Love | Like | Neutral | Dislike]
- musg_synthwave — Music: Synthwave — Taste for Synthwave music. — [Love | Like | Neutral | Dislike]
- musg_trap — Music: Trap — Taste for Trap music. — [Love | Like | Neutral | Dislike]
- musg_bollywood — Music: Bollywood — Taste for Bollywood music. — [Love | Like | Neutral | Dislike]
- filmg_action — Film: Action — Taste for action films. — [Love | Like | Neutral | Dislike]
- filmg_adventure — Film: Adventure — Taste for adventure films. — [Love | Like | Neutral | Dislike]
- filmg_comedy — Film: Comedy — Taste for comedy films. — [Love | Like | Neutral | Dislike]
- filmg_drama — Film: Drama — Taste for drama films. — [Love | Like | Neutral | Dislike]
- filmg_horror — Film: Horror — Taste for horror films. — [Love | Like | Neutral | Dislike]
- filmg_thriller — Film: Thriller — Taste for thriller films. — [Love | Like | Neutral | Dislike]
- filmg_sci_fi — Film: Sci-fi — Taste for sci-fi films. — [Love | Like | Neutral | Dislike]
- filmg_fantasy — Film: Fantasy — Taste for fantasy films. — [Love | Like | Neutral | Dislike]
- filmg_romance — Film: Romance — Taste for romance films. — [Love | Like | Neutral | Dislike]
- filmg_documentary — Film: Documentary — Taste for documentary films. — [Love | Like | Neutral | Dislike]
- filmg_animation — Film: Animation — Taste for animation films. — [Love | Like | Neutral | Dislike]
- filmg_crime — Film: Crime — Taste for crime films. — [Love | Like | Neutral | Dislike]
- filmg_mystery — Film: Mystery — Taste for mystery films. — [Love | Like | Neutral | Dislike]
- filmg_historical — Film: Historical — Taste for historical films. — [Love | Like | Neutral | Dislike]
- filmg_war — Film: War — Taste for war films. — [Love | Like | Neutral | Dislike]
- filmg_western — Film: Western — Taste for western films. — [Love | Like | Neutral | Dislike]
- filmg_musical — Film: Musical — Taste for musical films. — [Love | Like | Neutral | Dislike]
- filmg_noir — Film: Noir — Taste for noir films. — [Love | Like | Neutral | Dislike]
- filmg_superhero — Film: Superhero — Taste for superhero films. — [Love | Like | Neutral | Dislike]
- filmg_indie_film — Film: Indie film — Taste for indie film films. — [Love | Like | Neutral | Dislike]
- filmg_art_house — Film: Art house — Taste for art house films. — [Love | Like | Neutral | Dislike]
- filmg_biopic — Film: Biopic — Taste for biopic films. — [Love | Like | Neutral | Dislike]
- filmg_comedy_drama — Film: Comedy-drama — Taste for comedy-drama films. — [Love | Like | Neutral | Dislike]
- filmg_disaster — Film: Disaster — Taste for disaster films. — [Love | Like | Neutral | Dislike]
- bookg_literary_fiction — Books: Literary fiction — Taste for literary fiction. — [Love | Like | Neutral | Dislike]
- bookg_science_fiction — Books: Science fiction — Taste for science fiction. — [Love | Like | Neutral | Dislike]
- bookg_fantasy — Books: Fantasy — Taste for fantasy. — [Love | Like | Neutral | Dislike]
- bookg_mystery — Books: Mystery — Taste for mystery. — [Love | Like | Neutral | Dislike]
- bookg_thriller — Books: Thriller — Taste for thriller. — [Love | Like | Neutral | Dislike]
- bookg_romance — Books: Romance — Taste for romance. — [Love | Like | Neutral | Dislike]
- bookg_historical_fiction — Books: Historical fiction — Taste for historical fiction. — [Love | Like | Neutral | Dislike]
- bookg_horror — Books: Horror — Taste for horror. — [Love | Like | Neutral | Dislike]
- bookg_biography — Books: Biography — Taste for biography. — [Love | Like | Neutral | Dislike]
- bookg_memoir — Books: Memoir — Taste for memoir. — [Love | Like | Neutral | Dislike]
- bookg_self_help — Books: Self-help — Taste for self-help. — [Love | Like | Neutral | Dislike]
- bookg_business — Books: Business — Taste for business. — [Love | Like | Neutral | Dislike]
- bookg_popular_science — Books: Popular science — Taste for popular science. — [Love | Like | Neutral | Dislike]
- bookg_history — Books: History — Taste for history. — [Love | Like | Neutral | Dislike]
- bookg_philosophy — Books: Philosophy — Taste for philosophy. — [Love | Like | Neutral | Dislike]
- bookg_poetry — Books: Poetry — Taste for poetry. — [Love | Like | Neutral | Dislike]
- bookg_young_adult — Books: Young adult — Taste for young adult. — [Love | Like | Neutral | Dislike]
- bookg_graphic_novels — Books: Graphic novels — Taste for graphic novels. — [Love | Like | Neutral | Dislike]
- bookg_true_crime — Books: True crime — Taste for true crime. — [Love | Like | Neutral | Dislike]
- bookg_travel_writing — Books: Travel writing — Taste for travel writing. — [Love | Like | Neutral | Dislike]
- bookg_cookbooks — Books: Cookbooks — Taste for cookbooks. — [Love | Like | Neutral | Dislike]
- bookg_essays — Books: Essays — Taste for essays. — [Love | Like | Neutral | Dislike]

INPUT:

{{input_json}}
