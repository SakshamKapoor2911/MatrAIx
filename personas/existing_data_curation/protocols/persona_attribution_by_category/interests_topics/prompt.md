You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Interests: Topics  (78 dimensions)

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
- topic_politics — Interest: Politics — Level of interest in politics. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_sports — Interest: Sports — Level of interest in sports. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_travel — Interest: Travel — Level of interest in travel. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_cooking — Interest: Cooking — Level of interest in cooking. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_gaming — Interest: Gaming — Level of interest in gaming. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_fashion — Interest: Fashion — Level of interest in fashion. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_technology — Interest: Technology — Level of interest in technology. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_science — Interest: Science — Level of interest in science. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_space — Interest: Space — Level of interest in space. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_personal_finance — Interest: Personal finance — Level of interest in personal finance. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_investing — Interest: Investing — Level of interest in investing. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_cryptocurrency — Interest: Cryptocurrency — Level of interest in cryptocurrency. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_real_estate — Interest: Real estate — Level of interest in real estate. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_parenting — Interest: Parenting — Level of interest in parenting. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_pets — Interest: Pets — Level of interest in pets. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_gardening — Interest: Gardening — Level of interest in gardening. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_home_improvement — Interest: Home improvement — Level of interest in home improvement. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_cars — Interest: Cars — Level of interest in cars. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_motorcycles — Interest: Motorcycles — Level of interest in motorcycles. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_cycling — Interest: Cycling — Level of interest in cycling. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_running — Interest: Running — Level of interest in running. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_photography — Interest: Photography — Level of interest in photography. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_film — Interest: Film — Level of interest in film. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_tv_series — Interest: TV series — Level of interest in tv series. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_anime — Interest: Anime — Level of interest in anime. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_comics — Interest: Comics — Level of interest in comics. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_music — Interest: Music — Level of interest in music. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_live_concerts — Interest: Live concerts — Level of interest in live concerts. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_theater — Interest: Theater — Level of interest in theater. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_visual_art — Interest: Visual art — Level of interest in visual art. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_literature — Interest: Literature — Level of interest in literature. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_poetry — Interest: Poetry — Level of interest in poetry. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_history — Interest: History — Level of interest in history. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_philosophy — Interest: Philosophy — Level of interest in philosophy. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_religion — Interest: Religion — Level of interest in religion. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_meditation — Interest: Meditation — Level of interest in meditation. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_yoga — Interest: Yoga — Level of interest in yoga. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_hiking — Interest: Hiking — Level of interest in hiking. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_camping — Interest: Camping — Level of interest in camping. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_fishing — Interest: Fishing — Level of interest in fishing. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_birdwatching — Interest: Birdwatching — Level of interest in birdwatching. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_board_games — Interest: Board games — Level of interest in board games. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_tabletop_rpgs — Interest: Tabletop RPGs — Level of interest in tabletop rpgs. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_puzzles — Interest: Puzzles — Level of interest in puzzles. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_chess — Interest: Chess — Level of interest in chess. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_astrology — Interest: Astrology — Level of interest in astrology. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_true_crime — Interest: True crime — Level of interest in true crime. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_podcasts — Interest: Podcasts — Level of interest in podcasts. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_social_media — Interest: Social media — Level of interest in social media. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_volunteering — Interest: Volunteering — Level of interest in volunteering. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_activism — Interest: Activism — Level of interest in activism. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_environment — Interest: Environment — Level of interest in environment. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_sustainability — Interest: Sustainability — Level of interest in sustainability. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_wine — Interest: Wine — Level of interest in wine. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_coffee — Interest: Coffee — Level of interest in coffee. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_craft_beer — Interest: Craft beer — Level of interest in craft beer. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_tea — Interest: Tea — Level of interest in tea. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_baking — Interest: Baking — Level of interest in baking. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_interior_design — Interest: Interior design — Level of interest in interior design. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_architecture — Interest: Architecture — Level of interest in architecture. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_languages — Interest: Languages — Level of interest in languages. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_genealogy — Interest: Genealogy — Level of interest in genealogy. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_collecting — Interest: Collecting — Level of interest in collecting. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_knitting — Interest: Knitting — Level of interest in knitting. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_woodworking — Interest: Woodworking — Level of interest in woodworking. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_calligraphy — Interest: Calligraphy — Level of interest in calligraphy. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_dance — Interest: Dance — Level of interest in dance. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_stand_up_comedy — Interest: Stand-up comedy — Level of interest in stand-up comedy. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_magic_tricks — Interest: Magic tricks — Level of interest in magic tricks. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_astronomy — Interest: Astronomy — Level of interest in astronomy. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_robotics — Interest: Robotics — Level of interest in robotics. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_drones — Interest: Drones — Level of interest in drones. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_3d_printing — Interest: 3D printing — Level of interest in 3d printing. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_investmentoring — Interest: Investmentoring — Level of interest in investmentoring. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_entrepreneurship — Interest: Entrepreneurship — Level of interest in entrepreneurship. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_productivity — Interest: Productivity — Level of interest in productivity. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_self_improvement — Interest: Self-improvement — Level of interest in self-improvement. — [Passionate | Interested | Neutral | Indifferent | Averse]
- topic_mindfulness — Interest: Mindfulness — Level of interest in mindfulness. — [Passionate | Interested | Neutral | Indifferent | Averse]

INPUT:

{{input_json}}
