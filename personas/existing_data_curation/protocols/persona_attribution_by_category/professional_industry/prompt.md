You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Professional: Industry  (52 dimensions)

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
- company_size — Company size — Size/type of employing organization. — [Solo / freelance | Startup (<50) | SMB (50–500) | Mid (500–5k) | Enterprise (5k+) | Public sector | Academia | NGO]
- role_function — Role function — Job function. — [Engineering | Product | Research | Design | Sales / GTM | Marketing | Operations | Finance | HR | Legal | Clinical | Teaching | Executive]
- ind_technology — Industry: Technology — Work experience in technology. — [Veteran | Experienced | Some exposure | None]
- ind_healthcare — Industry: Healthcare — Work experience in healthcare. — [Veteran | Experienced | Some exposure | None]
- ind_finance — Industry: Finance — Work experience in finance. — [Veteran | Experienced | Some exposure | None]
- ind_banking — Industry: Banking — Work experience in banking. — [Veteran | Experienced | Some exposure | None]
- ind_insurance — Industry: Insurance — Work experience in insurance. — [Veteran | Experienced | Some exposure | None]
- ind_retail — Industry: Retail — Work experience in retail. — [Veteran | Experienced | Some exposure | None]
- ind_e_commerce — Industry: E-commerce — Work experience in e-commerce. — [Veteran | Experienced | Some exposure | None]
- ind_manufacturing — Industry: Manufacturing — Work experience in manufacturing. — [Veteran | Experienced | Some exposure | None]
- ind_automotive — Industry: Automotive — Work experience in automotive. — [Veteran | Experienced | Some exposure | None]
- ind_aerospace — Industry: Aerospace — Work experience in aerospace. — [Veteran | Experienced | Some exposure | None]
- ind_energy — Industry: Energy — Work experience in energy. — [Veteran | Experienced | Some exposure | None]
- ind_oil_gas — Industry: Oil & gas — Work experience in oil & gas. — [Veteran | Experienced | Some exposure | None]
- ind_utilities — Industry: Utilities — Work experience in utilities. — [Veteran | Experienced | Some exposure | None]
- ind_construction — Industry: Construction — Work experience in construction. — [Veteran | Experienced | Some exposure | None]
- ind_real_estate — Industry: Real estate — Work experience in real estate. — [Veteran | Experienced | Some exposure | None]
- ind_hospitality — Industry: Hospitality — Work experience in hospitality. — [Veteran | Experienced | Some exposure | None]
- ind_travel_tourism — Industry: Travel & tourism — Work experience in travel & tourism. — [Veteran | Experienced | Some exposure | None]
- ind_restaurants — Industry: Restaurants — Work experience in restaurants. — [Veteran | Experienced | Some exposure | None]
- ind_agriculture — Industry: Agriculture — Work experience in agriculture. — [Veteran | Experienced | Some exposure | None]
- ind_food_beverage — Industry: Food & beverage — Work experience in food & beverage. — [Veteran | Experienced | Some exposure | None]
- ind_pharmaceuticals — Industry: Pharmaceuticals — Work experience in pharmaceuticals. — [Veteran | Experienced | Some exposure | None]
- ind_biotech — Industry: Biotech — Work experience in biotech. — [Veteran | Experienced | Some exposure | None]
- ind_media — Industry: Media — Work experience in media. — [Veteran | Experienced | Some exposure | None]
- ind_entertainment — Industry: Entertainment — Work experience in entertainment. — [Veteran | Experienced | Some exposure | None]
- ind_gaming — Industry: Gaming — Work experience in gaming. — [Veteran | Experienced | Some exposure | None]
- ind_publishing — Industry: Publishing — Work experience in publishing. — [Veteran | Experienced | Some exposure | None]
- ind_advertising — Industry: Advertising — Work experience in advertising. — [Veteran | Experienced | Some exposure | None]
- ind_government — Industry: Government — Work experience in government. — [Veteran | Experienced | Some exposure | None]
- ind_defense — Industry: Defense — Work experience in defense. — [Veteran | Experienced | Some exposure | None]
- ind_nonprofit — Industry: Nonprofit — Work experience in nonprofit. — [Veteran | Experienced | Some exposure | None]
- ind_logistics — Industry: Logistics — Work experience in logistics. — [Veteran | Experienced | Some exposure | None]
- ind_transportation — Industry: Transportation — Work experience in transportation. — [Veteran | Experienced | Some exposure | None]
- ind_shipping — Industry: Shipping — Work experience in shipping. — [Veteran | Experienced | Some exposure | None]
- ind_mining — Industry: Mining — Work experience in mining. — [Veteran | Experienced | Some exposure | None]
- ind_chemicals — Industry: Chemicals — Work experience in chemicals. — [Veteran | Experienced | Some exposure | None]
- ind_textiles — Industry: Textiles — Work experience in textiles. — [Veteran | Experienced | Some exposure | None]
- ind_apparel — Industry: Apparel — Work experience in apparel. — [Veteran | Experienced | Some exposure | None]
- ind_consumer_electronics — Industry: Consumer electronics — Work experience in consumer electronics. — [Veteran | Experienced | Some exposure | None]
- ind_semiconductors — Industry: Semiconductors — Work experience in semiconductors. — [Veteran | Experienced | Some exposure | None]
- ind_legal_services — Industry: Legal services — Work experience in legal services. — [Veteran | Experienced | Some exposure | None]
- ind_consulting — Industry: Consulting — Work experience in consulting. — [Veteran | Experienced | Some exposure | None]
- ind_accounting — Industry: Accounting — Work experience in accounting. — [Veteran | Experienced | Some exposure | None]
- ind_marketing_agencies — Industry: Marketing agencies — Work experience in marketing agencies. — [Veteran | Experienced | Some exposure | None]
- ind_fitness_wellness — Industry: Fitness & wellness — Work experience in fitness & wellness. — [Veteran | Experienced | Some exposure | None]
- ind_beauty_cosmetics — Industry: Beauty & cosmetics — Work experience in beauty & cosmetics. — [Veteran | Experienced | Some exposure | None]
- ind_sports — Industry: Sports — Work experience in sports. — [Veteran | Experienced | Some exposure | None]
- ind_music — Industry: Music — Work experience in music. — [Veteran | Experienced | Some exposure | None]
- ind_fine_art — Industry: Fine art — Work experience in fine art. — [Veteran | Experienced | Some exposure | None]
- code_function_length — Function/Method Length Preference — Preference for small focused functions vs larger multi-purpose functions. — [Very small functions (5-10 lines) | Small functions (10-30 lines) | Medium functions (30-100 lines) | Large functions (100+ lines) | Varies by context]
- wiki_occupation — Occupation — Primary profession or occupational field from real biographical data. — [Scientist | Politician | Artist | Athlete | Entrepreneur | Entertainer | Academic | Military | Religious | Other]

INPUT:

{{input_json}}
