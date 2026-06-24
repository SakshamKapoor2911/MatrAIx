You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Interests: Sports  (40 dimensions)

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
- sport_soccer — Sport: Soccer — Relationship to soccer. — [Play | Follow | Casual | None]
- sport_basketball — Sport: Basketball — Relationship to basketball. — [Play | Follow | Casual | None]
- sport_american_football — Sport: American football — Relationship to american football. — [Play | Follow | Casual | None]
- sport_baseball — Sport: Baseball — Relationship to baseball. — [Play | Follow | Casual | None]
- sport_tennis — Sport: Tennis — Relationship to tennis. — [Play | Follow | Casual | None]
- sport_golf — Sport: Golf — Relationship to golf. — [Play | Follow | Casual | None]
- sport_cricket — Sport: Cricket — Relationship to cricket. — [Play | Follow | Casual | None]
- sport_rugby — Sport: Rugby — Relationship to rugby. — [Play | Follow | Casual | None]
- sport_hockey — Sport: Hockey — Relationship to hockey. — [Play | Follow | Casual | None]
- sport_volleyball — Sport: Volleyball — Relationship to volleyball. — [Play | Follow | Casual | None]
- sport_swimming — Sport: Swimming — Relationship to swimming. — [Play | Follow | Casual | None]
- sport_running — Sport: Running — Relationship to running. — [Play | Follow | Casual | None]
- sport_cycling — Sport: Cycling — Relationship to cycling. — [Play | Follow | Casual | None]
- sport_boxing — Sport: Boxing — Relationship to boxing. — [Play | Follow | Casual | None]
- sport_mma — Sport: MMA — Relationship to mma. — [Play | Follow | Casual | None]
- sport_wrestling — Sport: Wrestling — Relationship to wrestling. — [Play | Follow | Casual | None]
- sport_skiing — Sport: Skiing — Relationship to skiing. — [Play | Follow | Casual | None]
- sport_snowboarding — Sport: Snowboarding — Relationship to snowboarding. — [Play | Follow | Casual | None]
- sport_surfing — Sport: Surfing — Relationship to surfing. — [Play | Follow | Casual | None]
- sport_skateboarding — Sport: Skateboarding — Relationship to skateboarding. — [Play | Follow | Casual | None]
- sport_climbing — Sport: Climbing — Relationship to climbing. — [Play | Follow | Casual | None]
- sport_gymnastics — Sport: Gymnastics — Relationship to gymnastics. — [Play | Follow | Casual | None]
- sport_track_field — Sport: Track & field — Relationship to track & field. — [Play | Follow | Casual | None]
- sport_badminton — Sport: Badminton — Relationship to badminton. — [Play | Follow | Casual | None]
- sport_table_tennis — Sport: Table tennis — Relationship to table tennis. — [Play | Follow | Casual | None]
- sport_squash — Sport: Squash — Relationship to squash. — [Play | Follow | Casual | None]
- sport_sailing — Sport: Sailing — Relationship to sailing. — [Play | Follow | Casual | None]
- sport_rowing — Sport: Rowing — Relationship to rowing. — [Play | Follow | Casual | None]
- sport_martial_arts — Sport: Martial arts — Relationship to martial arts. — [Play | Follow | Casual | None]
- sport_yoga — Sport: Yoga — Relationship to yoga. — [Play | Follow | Casual | None]
- sport_pilates — Sport: Pilates — Relationship to pilates. — [Play | Follow | Casual | None]
- sport_crossfit — Sport: CrossFit — Relationship to crossfit. — [Play | Follow | Casual | None]
- sport_weightlifting — Sport: Weightlifting — Relationship to weightlifting. — [Play | Follow | Casual | None]
- sport_esports — Sport: Esports — Relationship to esports. — [Play | Follow | Casual | None]
- sport_darts — Sport: Darts — Relationship to darts. — [Play | Follow | Casual | None]
- sport_bowling — Sport: Bowling — Relationship to bowling. — [Play | Follow | Casual | None]
- sport_archery — Sport: Archery — Relationship to archery. — [Play | Follow | Casual | None]
- sport_equestrian — Sport: Equestrian — Relationship to equestrian. — [Play | Follow | Casual | None]
- sport_fencing — Sport: Fencing — Relationship to fencing. — [Play | Follow | Casual | None]
- sport_triathlon — Sport: Triathlon — Relationship to triathlon. — [Play | Follow | Casual | None]

INPUT:

{{input_json}}
