# Persona Attribute Schema Scaffold

This folder summarizes the 1,339-attribute persona schema as a planning layer for distribution-aware persona generation. It is schema-level metadata, not tied to any downstream dataset.

Source schema used to generate this first pass: `MatrAIx-v1-evaluation-flow/personas/dimensions+new.json`.

## Step 1: Attribute Metadata

`attribute_metadata.csv` contains one row per schema attribute with: `attribute_name`, `attribute_type`, `value_type`, `allowed_values`, `module`, `parents`, `required_context`, `source_of_distribution`, `constraint_type`, and `is_core`.

`module_summary.csv` groups the 1,339 attributes into 10-20 broad modules so downstream modeling can use `macro variables -> latent factors -> modules -> individual attributes` instead of building a dense graph over all attributes.

| module | attributes | primary source | example attributes |
|---|---:|---|---|
| expertise_skills | 201 | education/work profile/survey/model-derived | domain, subject_specialty, expertise_gap, fam_machine_learning, fam_deep_learning, fam_statistics, fam_data_science, fam_cardiology |
| product_category_interests | 197 | survey/platform behavior/inferred | topic_politics, topic_sports, topic_cooking, topic_fashion, topic_technology, topic_science, topic_space, topic_investing |
| media_culture | 161 | survey/platform behavior/inferred | media_diet, topic_gaming, topic_tv_series, topic_music, topic_social_media, att_social_media, cult_united_states, cult_canada |
| technology_digital | 120 | survey/inferred behavior/model-derived | tech_savviness, fam_computer_networking, fam_computer_graphics, fam_computer_vision, fam_human_computer_interaction, skill_spreadsheet_modeling, skill_technical_writing, tool_excel |
| values_beliefs | 104 | WVS/GSS/Pew/survey | values_priority, political_lean, religiosity, trust_level, safety_sensitivity, fam_political_science, fam_religious_studies, topic_spirituality |
| personality_psychometrics | 96 | psychometric survey/model-derived | domain_characteristics, dominant_trait, neurotype, mbti_type, big5_imagination, big5_artistic_interest, big5_emotionality, big5_adventurousness |
| external_dataset_mappings | 94 | external persona datasets/model mapping | personahub_dimension_1, personahub_dimension_2, oasis_dimension_1, oasis_dimension_2, oasis_dimension_3, oasis_dimension_4, oasis_dimension_5, oasis_dimension_6 |
| language_communication | 89 | census/ACS/survey/inferred text | primary_language, english_proficiency, multilingualism, tone_expected, lang_english, lang_mandarin, lang_cantonese, lang_spanish |
| lifestyle | 66 | survey/platform behavior/inferred | time_pressure, modality_pref, accessibility_needs, lstyle_sleep_schedule, lstyle_work_schedule, peeve_typos, peeve_being_interrupted, peeve_lateness |
| work_career | 60 | census/ACS/BLS/CPS/OES | research_output, seniority, company_size, role_function, years_experience, linkedin_activity, ind_technology, ind_healthcare |
| demographics | 45 | census/ACS/survey | age_bracket, gender_identity, socioeconomic_band, register, cultural_background, att_immigration, att_traditional_gender_roles, demo_employment_status |
| education | 39 | census/ACS/NCES/survey | highest_education, academic_field, institution_tier, learning_style, fam_special_education, att_higher_education, ind_education, acad_algebra |
| health | 36 | CDC/NHIS/BRFSS/survey | topic_fitness, ind_fitness_wellness, lstyle_exercise_freq, lstyle_diet_type, lstyle_alcohol_use, health_general_health, health_chronic_condition, health_mobility |
| household_family | 9 | census/ACS/survey | life_stage, major_life_events, lstyle_household_size, val_family, demo_marital_status, demo_children_count, demo_household_income, schwartz_value_tradition |
| risk_decision | 7 | survey/psychometric scale/model-derived | risk_tolerance, decision_style, need_for_closure, dospert_ethical_risk_tolerance, dospert_financial_risk_tolerance, dospert_recreational_risk_tolerance, dospert_social_risk_tolerance |
| income_finance | 5 | census/ACS/CPS/consumer finance survey | economic_motivation, topic_personal_finance, att_universal_basic_income, val_wealth, habit_budget_tracking |
| state_context | 5 | session/task context | emotional_state, intent, query_complexity, prior_context, device_context |
| geography | 4 | census/ACS/IPUMS | region, urbanicity, wiki_birth_place, nemotron_state |
| travel_mobility | 1 | ACS commute/travel survey/inferred behavior | topic_travel |

## Step 2: Macro Scaffold

`macro_scaffold.csv` lists census/survey-sourceable macro variables and local conditional distributions for ancestral sampling.

| macro variable | schema attribute | parents | source | local conditional |
|---|---|---|---|---|
| country | new scaffold variable | root | census/IPUMS/UN population | `P(country)` |
| region_state | region | country | census/ACS/IPUMS/geocoding | `P(region_state \| country)` |
| urbanicity | urbanicity | country, region_state | census/ACS/rural-urban codes | `P(urbanicity \| country, region_state)` |
| age_bucket | age_bracket | country, region_state | census/ACS/IPUMS | `P(age_bucket \| country, region_state)` |
| gender | gender_identity | country, age_bucket | census/ACS/survey | `P(gender \| country, age_bucket)` |
| language | primary_language | country, region_state, age_bucket | census/ACS language-at-home/survey | `P(language \| country, region_state, age_bucket)` |
| education_level | highest_education | country, age_bucket, gender | census/ACS/NCES | `P(education_level \| country, age_bucket, gender)` |
| employment_status | new scaffold variable | country, age_bucket, education_level | ACS/CPS/labor force survey | `P(employment_status \| country, age_bucket, education_level)` |
| occupation_family | role_function | country, age_bucket, education_level, employment_status | ACS/CPS/BLS/OES/ISCO/SOC | `P(occupation_family \| country, age_bucket, education_level, employment_status)` |
| income_bucket | socioeconomic_band | country, occupation_family, education_level, age_bucket | census/ACS/CPS income tables | `P(income_bucket \| country, occupation_family, education_level, age_bucket)` |
| household_type | life_stage | country, age_bucket, income_bucket | census/ACS household/family tables | `P(household_type \| country, age_bucket, income_bucket)` |
| marital_status | new scaffold variable | country, age_bucket, gender | census/ACS | `P(marital_status \| country, age_bucket, gender)` |
| children_status | new scaffold variable | country, age_bucket, household_type, marital_status | census/ACS fertility/household tables | `P(children_status \| country, age_bucket, household_type, marital_status)` |
| english_proficiency | english_proficiency | country, language, education_level | census/ACS language proficiency/survey | `P(english_proficiency \| country, language, education_level)` |
| digital_fluency | tech_savviness | age_bucket, education_level, occupation_family, urbanicity, income_bucket | survey/NTIA/Eurostat/OECD/model-derived | `P(digital_fluency \| age_bucket, education_level, occupation_family, urbanicity, income_bucket)` |

Use local conditionals rather than a complete joint table. Prioritize Census/ACS/IPUMS, national statistical offices, labor statistics, and reputable surveys. Use model-estimated priors only as fallback.

## Step 3: Latent Factor Layer

`latent_factors.csv` defines the intermediate factor layer between macro variables and the 1,339 attributes. These factors prevent every individual attribute from independently depending on the full macro scaffold. Most factors use a 1-5 ordinal scale, where `1` is very low and `5` is very high.

| latent factor | parents | local conditional | downstream modules |
|---|---|---|---|
| SES | country, region_state, education_level, occupation_family, income_bucket, household_type | `P(SES \| country, region_state, education_level, occupation_family, income_bucket, household_type)` | demographics, income_finance, education, work_career, shopping_commerce, health |
| life_stage | age_bucket, employment_status, marital_status, children_status, household_type | `P(life_stage \| age_bucket, employment_status, marital_status, children_status, household_type)` | household_family, work_career, lifestyle, shopping_commerce, health |
| urban_lifestyle | country, region_state, urbanicity, income_bucket, occupation_family | `P(urban_lifestyle \| country, region_state, urbanicity, income_bucket, occupation_family)` | geography, lifestyle, travel_mobility, shopping_commerce, media_culture |
| digital_fluency | age_bucket, education_level, occupation_family, income_bucket, urbanicity | `P(digital_fluency \| age_bucket, education_level, occupation_family, income_bucket, urbanicity)` | technology_digital, shopping_commerce, media_culture, expertise_skills, language_communication |
| price_sensitivity | income_bucket, SES, household_type, children_status, country | `P(price_sensitivity \| income_bucket, SES, household_type, children_status, country)` | shopping_commerce, income_finance, product_category_interests, lifestyle |
| risk_tolerance | age_bucket, income_bucket, education_level, occupation_family, gender | `P(risk_tolerance \| age_bucket, income_bucket, education_level, occupation_family, gender)` | risk_decision, income_finance, values_beliefs, product_category_interests, personality_psychometrics |
| novelty_seeking | age_bucket, education_level, urbanicity, digital_fluency, country | `P(novelty_seeking \| age_bucket, education_level, urbanicity, digital_fluency, country)` | personality_psychometrics, media_culture, product_category_interests, technology_digital, shopping_commerce |
| health_orientation | age_bucket, gender, country, income_bucket, education_level | `P(health_orientation \| age_bucket, gender, country, income_bucket, education_level)` | health, lifestyle, product_category_interests, values_beliefs |
| family_responsibility | age_bucket, marital_status, children_status, household_type, employment_status | `P(family_responsibility \| age_bucket, marital_status, children_status, household_type, employment_status)` | household_family, lifestyle, shopping_commerce, values_beliefs, health |
| career_orientation | age_bucket, education_level, employment_status, occupation_family, income_bucket | `P(career_orientation \| age_bucket, education_level, employment_status, occupation_family, income_bucket)` | work_career, education, expertise_skills, values_beliefs, lifestyle |
| social_orientation | age_bucket, country, urbanicity, household_type, digital_fluency | `P(social_orientation \| age_bucket, country, urbanicity, household_type, digital_fluency)` | personality_psychometrics, values_beliefs, media_culture, language_communication, lifestyle |
| environmental_consciousness | country, education_level, age_bucket, urbanicity, income_bucket | `P(environmental_consciousness \| country, education_level, age_bucket, urbanicity, income_bucket)` | values_beliefs, shopping_commerce, product_category_interests, lifestyle |
| brand_consciousness | income_bucket, SES, age_bucket, urbanicity, media_culture | `P(brand_consciousness \| income_bucket, SES, age_bucket, urbanicity, media_culture)` | shopping_commerce, product_category_interests, media_culture, values_beliefs |
| time_scarcity | employment_status, occupation_family, children_status, household_type, urban_lifestyle | `P(time_scarcity \| employment_status, occupation_family, children_status, household_type, urban_lifestyle)` | lifestyle, shopping_commerce, technology_digital, language_communication |
| financial_security_orientation | income_bucket, SES, age_bucket, household_type, children_status, employment_status | `P(financial_security_orientation \| income_bucket, SES, age_bucket, household_type, children_status, employment_status)` | income_finance, risk_decision, values_beliefs, shopping_commerce, lifestyle |

Example dependency pattern:

`prefers_online_shopping`, `uses_productivity_apps`, `adopts_new_tech_early`, and `prefers_digital_payments` should share parents like `digital_fluency`, `age_bucket`, `income_bucket`, and `urbanicity`, instead of being sampled as unrelated attributes.
