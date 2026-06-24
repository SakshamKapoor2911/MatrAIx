You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Worldview: Beliefs  (68 dimensions)

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
- political_lean — Political lean — Broad political orientation. — [Left | Center-left | Center | Center-right | Right | Apolitical]
- trust_level — Trust level — How much they trust the agent. — [Trusting | Verifying | Skeptical | Hostile]
- safety_sensitivity — Safety sensitivity — Risk class of the request. — [Benign | Sensitive personal | High-stakes (medical/legal/financial) | Potentially harmful | Dual-use]
- fam_political_science — Familiarity: Political science — How well the persona knows Political science. — [Expert | Proficient | Familiar | Aware | None]
- fam_religious_studies — Familiarity: Religious studies — How well the persona knows Religious studies. — [Expert | Proficient | Familiar | Aware | None]
- topic_spirituality — Interest: Spirituality — Level of interest in spirituality. — [Passionate | Interested | Neutral | Indifferent | Averse]
- att_ai — Attitude: AI — Stance toward ai. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_automation — Attitude: Automation — Stance toward automation. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_data_privacy — Attitude: Data privacy — Stance toward data privacy. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_social_media — Attitude: Social media — Stance toward social media. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_remote_work — Attitude: Remote work — Stance toward remote work. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_globalization — Attitude: Globalization — Stance toward globalization. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_free_markets — Attitude: Free markets — Stance toward free markets. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_government_regulation — Attitude: Government regulation — Stance toward government regulation. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_climate_action — Attitude: Climate action — Stance toward climate action. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_nuclear_energy — Attitude: Nuclear energy — Stance toward nuclear energy. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_renewable_energy — Attitude: Renewable energy — Stance toward renewable energy. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_genetic_engineering — Attitude: Genetic engineering — Stance toward genetic engineering. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_vaccines — Attitude: Vaccines — Stance toward vaccines. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_alternative_medicine — Attitude: Alternative medicine — Stance toward alternative medicine. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_organized_religion — Attitude: Organized religion — Stance toward organized religion. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_cryptocurrency — Attitude: Cryptocurrency — Stance toward cryptocurrency. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_the_gig_economy — Attitude: The gig economy — Stance toward the gig economy. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_labor_unions — Attitude: Labor unions — Stance toward labor unions. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_higher_education — Attitude: Higher education — Stance toward higher education. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_homeownership — Attitude: Homeownership — Stance toward homeownership. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_taking_on_debt — Attitude: Taking on debt — Stance toward taking on debt. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_risk_taking — Attitude: Risk-taking — Stance toward risk-taking. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_authority — Attitude: Authority — Stance toward authority. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_rapid_change — Attitude: Rapid change — Stance toward rapid change. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_new_technology — Attitude: New technology — Stance toward new technology. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_brand_loyalty — Attitude: Brand loyalty — Stance toward brand loyalty. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_advertising — Attitude: Advertising — Stance toward advertising. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_influencers — Attitude: Influencers — Stance toward influencers. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_online_reviews — Attitude: Online reviews — Stance toward online reviews. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_subscription_services — Attitude: Subscription services — Stance toward subscription services. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_open_source — Attitude: Open source — Stance toward open source. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_surveillance — Attitude: Surveillance — Stance toward surveillance. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_self_driving_cars — Attitude: Self-driving cars — Stance toward self-driving cars. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_space_exploration — Attitude: Space exploration — Stance toward space exploration. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_universal_basic_income — Attitude: Universal basic income — Stance toward universal basic income. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_minimalism — Attitude: Minimalism — Stance toward minimalism. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_consumerism — Attitude: Consumerism — Stance toward consumerism. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_veganism — Attitude: Veganism — Stance toward veganism. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_fast_fashion — Attitude: Fast fashion — Stance toward fast fashion. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_gun_ownership — Attitude: Gun ownership — Stance toward gun ownership. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_capital_punishment — Attitude: Capital punishment — Stance toward capital punishment. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_free_speech — Attitude: Free speech — Stance toward free speech. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_privacy_vs_security — Attitude: Privacy vs security — Stance toward privacy vs security. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_globalized_supply_chains — Attitude: Globalized supply chains — Stance toward globalized supply chains. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_working_from_office — Attitude: Working from office — Stance toward working from office. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_four_day_work_week — Attitude: Four-day work week — Stance toward four-day work week. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_performance_reviews — Attitude: Performance reviews — Stance toward performance reviews. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_standardized_testing — Attitude: Standardized testing — Stance toward standardized testing. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_tipping_culture — Attitude: Tipping culture — Stance toward tipping culture. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_electric_vehicles — Attitude: Electric vehicles — Stance toward electric vehicles. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_public_transit — Attitude: Public transit — Stance toward public transit. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_urban_density — Attitude: Urban density — Stance toward urban density. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- att_gentrification — Attitude: Gentrification — Stance toward gentrification. — [Enthusiast | Positive | Neutral | Skeptical | Opposed]
- acad_political_theory — Subject: Political theory — Interest in political theory. — [Passionate | Interested | Neutral | Indifferent | Averse]
- mft_care_harm — Moral Foundation Care/Harm — Moral Foundations Theory construct: sensitivity to care versus harm. — [Very high | High | Average | Low | Very low]
- mft_fairness_cheating — Moral Foundation Fairness/Cheating — Moral Foundations Theory construct: sensitivity to fairness versus cheating. — [Very high | High | Average | Low | Very low]
- mft_loyalty_betrayal — Moral Foundation Loyalty/Betrayal — Moral Foundations Theory construct: sensitivity to loyalty versus betrayal. — [Very high | High | Average | Low | Very low]
- mft_authority_subversion — Moral Foundation Authority/Subversion — Moral Foundations Theory construct: sensitivity to authority versus subversion. — [Very high | High | Average | Low | Very low]
- mft_sanctity_degradation — Moral Foundation Sanctity/Degradation — Moral Foundations Theory construct: sensitivity to sanctity versus degradation. — [Very high | High | Average | Low | Very low]
- mft_liberty_oppression — Moral Foundation Liberty/Oppression — Moral Foundations Theory construct: sensitivity to liberty versus oppression. — [Very high | High | Average | Low | Very low]
- dospert_health_safety_risk_tolerance — DOSPERT Health/Safety Risk Tolerance — Domain-specific risk orientation for health and safety risks. — [Very high | High | Average | Low | Very low]
- wiki_political_affiliation — Political Affiliation — Political party or political ideology association. — [Democratic | Republican | Conservative | Labour | Green | Independent | Progressive | Socialist | Liberal | Other]

INPUT:

{{input_json}}
