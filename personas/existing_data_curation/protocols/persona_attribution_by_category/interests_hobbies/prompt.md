You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Interests: Hobbies  (50 dimensions)

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
- hob_knitting — Hobby: Knitting — Engagement with knitting. — [Avid | Active | Occasional | Curious | Never]
- hob_crocheting — Hobby: Crocheting — Engagement with crocheting. — [Avid | Active | Occasional | Curious | Never]
- hob_pottery — Hobby: Pottery — Engagement with pottery. — [Avid | Active | Occasional | Curious | Never]
- hob_woodworking — Hobby: Woodworking — Engagement with woodworking. — [Avid | Active | Occasional | Curious | Never]
- hob_metalworking — Hobby: Metalworking — Engagement with metalworking. — [Avid | Active | Occasional | Curious | Never]
- hob_leatherworking — Hobby: Leatherworking — Engagement with leatherworking. — [Avid | Active | Occasional | Curious | Never]
- hob_candle_making — Hobby: Candle making — Engagement with candle making. — [Avid | Active | Occasional | Curious | Never]
- hob_origami — Hobby: Origami — Engagement with origami. — [Avid | Active | Occasional | Curious | Never]
- hob_calligraphy — Hobby: Calligraphy — Engagement with calligraphy. — [Avid | Active | Occasional | Curious | Never]
- hob_scrapbooking — Hobby: Scrapbooking — Engagement with scrapbooking. — [Avid | Active | Occasional | Curious | Never]
- hob_quilting — Hobby: Quilting — Engagement with quilting. — [Avid | Active | Occasional | Curious | Never]
- hob_embroidery — Hobby: Embroidery — Engagement with embroidery. — [Avid | Active | Occasional | Curious | Never]
- hob_jewelry_making — Hobby: Jewelry making — Engagement with jewelry making. — [Avid | Active | Occasional | Curious | Never]
- hob_model_building — Hobby: Model building — Engagement with model building. — [Avid | Active | Occasional | Curious | Never]
- hob_coin_collecting — Hobby: Coin collecting — Engagement with coin collecting. — [Avid | Active | Occasional | Curious | Never]
- hob_stamp_collecting — Hobby: Stamp collecting — Engagement with stamp collecting. — [Avid | Active | Occasional | Curious | Never]
- hob_antiquing — Hobby: Antiquing — Engagement with antiquing. — [Avid | Active | Occasional | Curious | Never]
- hob_vegetable_gardening — Hobby: Vegetable gardening — Engagement with vegetable gardening. — [Avid | Active | Occasional | Curious | Never]
- hob_bonsai — Hobby: Bonsai — Engagement with bonsai. — [Avid | Active | Occasional | Curious | Never]
- hob_aquariums — Hobby: Aquariums — Engagement with aquariums. — [Avid | Active | Occasional | Curious | Never]
- hob_beekeeping — Hobby: Beekeeping — Engagement with beekeeping. — [Avid | Active | Occasional | Curious | Never]
- hob_birdwatching — Hobby: Birdwatching — Engagement with birdwatching. — [Avid | Active | Occasional | Curious | Never]
- hob_stargazing — Hobby: Stargazing — Engagement with stargazing. — [Avid | Active | Occasional | Curious | Never]
- hob_geocaching — Hobby: Geocaching — Engagement with geocaching. — [Avid | Active | Occasional | Curious | Never]
- hob_rock_climbing — Hobby: Rock climbing — Engagement with rock climbing. — [Avid | Active | Occasional | Curious | Never]
- hob_bouldering — Hobby: Bouldering — Engagement with bouldering. — [Avid | Active | Occasional | Curious | Never]
- hob_kayaking — Hobby: Kayaking — Engagement with kayaking. — [Avid | Active | Occasional | Curious | Never]
- hob_paddleboarding — Hobby: Paddleboarding — Engagement with paddleboarding. — [Avid | Active | Occasional | Curious | Never]
- hob_scuba_diving — Hobby: Scuba diving — Engagement with scuba diving. — [Avid | Active | Occasional | Curious | Never]
- hob_snorkeling — Hobby: Snorkeling — Engagement with snorkeling. — [Avid | Active | Occasional | Curious | Never]
- hob_skydiving — Hobby: Skydiving — Engagement with skydiving. — [Avid | Active | Occasional | Curious | Never]
- hob_paragliding — Hobby: Paragliding — Engagement with paragliding. — [Avid | Active | Occasional | Curious | Never]
- hob_horseback_riding — Hobby: Horseback riding — Engagement with horseback riding. — [Avid | Active | Occasional | Curious | Never]
- hob_foraging — Hobby: Foraging — Engagement with foraging. — [Avid | Active | Occasional | Curious | Never]
- hob_bread_baking — Hobby: Bread baking — Engagement with bread baking. — [Avid | Active | Occasional | Curious | Never]
- hob_home_brewing — Hobby: Home brewing — Engagement with home brewing. — [Avid | Active | Occasional | Curious | Never]
- hob_winemaking — Hobby: Winemaking — Engagement with winemaking. — [Avid | Active | Occasional | Curious | Never]
- hob_cheesemaking — Hobby: Cheesemaking — Engagement with cheesemaking. — [Avid | Active | Occasional | Curious | Never]
- hob_karaoke — Hobby: Karaoke — Engagement with karaoke. — [Avid | Active | Occasional | Curious | Never]
- hob_ballroom_dance — Hobby: Ballroom dance — Engagement with ballroom dance. — [Avid | Active | Occasional | Curious | Never]
- hob_salsa_dancing — Hobby: Salsa dancing — Engagement with salsa dancing. — [Avid | Active | Occasional | Curious | Never]
- hob_improv — Hobby: Improv — Engagement with improv. — [Avid | Active | Occasional | Curious | Never]
- hob_stand_up_comedy — Hobby: Stand-up comedy — Engagement with stand-up comedy. — [Avid | Active | Occasional | Curious | Never]
- hob_juggling — Hobby: Juggling — Engagement with juggling. — [Avid | Active | Occasional | Curious | Never]
- hob_whittling — Hobby: Whittling — Engagement with whittling. — [Avid | Active | Occasional | Curious | Never]
- hob_letterpress — Hobby: Letterpress — Engagement with letterpress. — [Avid | Active | Occasional | Curious | Never]
- hob_urban_sketching — Hobby: Urban sketching — Engagement with urban sketching. — [Avid | Active | Occasional | Curious | Never]
- hob_genealogy — Hobby: Genealogy — Engagement with genealogy. — [Avid | Active | Occasional | Curious | Never]
- hob_metal_detecting — Hobby: Metal detecting — Engagement with metal detecting. — [Avid | Active | Occasional | Curious | Never]
- hob_cosplay — Hobby: Cosplay — Engagement with cosplay. — [Avid | Active | Occasional | Curious | Never]

INPUT:

{{input_json}}
