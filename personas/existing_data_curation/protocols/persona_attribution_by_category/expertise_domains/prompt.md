You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Expertise: Domains  (144 dimensions)

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
- domain — Domain — Primary field of work or study. — [Software & AI | Healthcare & Medicine | Law & Policy | Finance & Economics | Education | Engineering | Natural Sciences | Social Sciences | Arts & Humanities | Business & Management | Agriculture | Manufacturing | Media & Journalism | Public Sector | Hospitality | Skilled Trades]
- subject_specialty — Subject specialty — Specific specialty within the domain. — [Machine learning | Cardiology | Constitutional law | Quant trading | Curriculum design | Structural engineering | Molecular biology | Behavioral economics | Comparative literature | Operations | Agronomy | Robotics | Investigative reporting | Urban planning | Culinary arts | Electrical work]
- tech_savviness — Tech savviness — Comfort with technology. — [Digital native | Comfortable | Cautious adopter | Reluctant | Avoidant]
- expertise_gap — Expertise gap — Their expertise relative to the task. — [Novice asking expert | Peer-level | Expert testing the system | Teaching the model]
- fam_machine_learning — Familiarity: Machine learning — How well the persona knows Machine learning. — [Expert | Proficient | Familiar | Aware | None]
- fam_deep_learning — Familiarity: Deep learning — How well the persona knows Deep learning. — [Expert | Proficient | Familiar | Aware | None]
- fam_statistics — Familiarity: Statistics — How well the persona knows Statistics. — [Expert | Proficient | Familiar | Aware | None]
- fam_data_science — Familiarity: Data science — How well the persona knows Data science. — [Expert | Proficient | Familiar | Aware | None]
- fam_cardiology — Familiarity: Cardiology — How well the persona knows Cardiology. — [Expert | Proficient | Familiar | Aware | None]
- fam_neurology — Familiarity: Neurology — How well the persona knows Neurology. — [Expert | Proficient | Familiar | Aware | None]
- fam_oncology — Familiarity: Oncology — How well the persona knows Oncology. — [Expert | Proficient | Familiar | Aware | None]
- fam_pediatrics — Familiarity: Pediatrics — How well the persona knows Pediatrics. — [Expert | Proficient | Familiar | Aware | None]
- fam_psychiatry — Familiarity: Psychiatry — How well the persona knows Psychiatry. — [Expert | Proficient | Familiar | Aware | None]
- fam_radiology — Familiarity: Radiology — How well the persona knows Radiology. — [Expert | Proficient | Familiar | Aware | None]
- fam_surgery — Familiarity: Surgery — How well the persona knows Surgery. — [Expert | Proficient | Familiar | Aware | None]
- fam_immunology — Familiarity: Immunology — How well the persona knows Immunology. — [Expert | Proficient | Familiar | Aware | None]
- fam_constitutional_law — Familiarity: Constitutional law — How well the persona knows Constitutional law. — [Expert | Proficient | Familiar | Aware | None]
- fam_contract_law — Familiarity: Contract law — How well the persona knows Contract law. — [Expert | Proficient | Familiar | Aware | None]
- fam_criminal_law — Familiarity: Criminal law — How well the persona knows Criminal law. — [Expert | Proficient | Familiar | Aware | None]
- fam_tax_law — Familiarity: Tax law — How well the persona knows Tax law. — [Expert | Proficient | Familiar | Aware | None]
- fam_intellectual_property — Familiarity: Intellectual property — How well the persona knows Intellectual property. — [Expert | Proficient | Familiar | Aware | None]
- fam_corporate_finance — Familiarity: Corporate finance — How well the persona knows Corporate finance. — [Expert | Proficient | Familiar | Aware | None]
- fam_quantitative_trading — Familiarity: Quantitative trading — How well the persona knows Quantitative trading. — [Expert | Proficient | Familiar | Aware | None]
- fam_accounting — Familiarity: Accounting — How well the persona knows Accounting. — [Expert | Proficient | Familiar | Aware | None]
- fam_auditing — Familiarity: Auditing — How well the persona knows Auditing. — [Expert | Proficient | Familiar | Aware | None]
- fam_macroeconomics — Familiarity: Macroeconomics — How well the persona knows Macroeconomics. — [Expert | Proficient | Familiar | Aware | None]
- fam_microeconomics — Familiarity: Microeconomics — How well the persona knows Microeconomics. — [Expert | Proficient | Familiar | Aware | None]
- fam_behavioral_economics — Familiarity: Behavioral economics — How well the persona knows Behavioral economics. — [Expert | Proficient | Familiar | Aware | None]
- fam_curriculum_design — Familiarity: Curriculum design — How well the persona knows Curriculum design. — [Expert | Proficient | Familiar | Aware | None]
- fam_pedagogy — Familiarity: Pedagogy — How well the persona knows Pedagogy. — [Expert | Proficient | Familiar | Aware | None]
- fam_structural_engineering — Familiarity: Structural engineering — How well the persona knows Structural engineering. — [Expert | Proficient | Familiar | Aware | None]
- fam_mechanical_engineering — Familiarity: Mechanical engineering — How well the persona knows Mechanical engineering. — [Expert | Proficient | Familiar | Aware | None]
- fam_electrical_engineering — Familiarity: Electrical engineering — How well the persona knows Electrical engineering. — [Expert | Proficient | Familiar | Aware | None]
- fam_civil_engineering — Familiarity: Civil engineering — How well the persona knows Civil engineering. — [Expert | Proficient | Familiar | Aware | None]
- fam_chemical_engineering — Familiarity: Chemical engineering — How well the persona knows Chemical engineering. — [Expert | Proficient | Familiar | Aware | None]
- fam_aerospace_engineering — Familiarity: Aerospace engineering — How well the persona knows Aerospace engineering. — [Expert | Proficient | Familiar | Aware | None]
- fam_robotics — Familiarity: Robotics — How well the persona knows Robotics. — [Expert | Proficient | Familiar | Aware | None]
- fam_control_systems — Familiarity: Control systems — How well the persona knows Control systems. — [Expert | Proficient | Familiar | Aware | None]
- fam_molecular_biology — Familiarity: Molecular biology — How well the persona knows Molecular biology. — [Expert | Proficient | Familiar | Aware | None]
- fam_genetics — Familiarity: Genetics — How well the persona knows Genetics. — [Expert | Proficient | Familiar | Aware | None]
- fam_biochemistry — Familiarity: Biochemistry — How well the persona knows Biochemistry. — [Expert | Proficient | Familiar | Aware | None]
- fam_organic_chemistry — Familiarity: Organic chemistry — How well the persona knows Organic chemistry. — [Expert | Proficient | Familiar | Aware | None]
- fam_physical_chemistry — Familiarity: Physical chemistry — How well the persona knows Physical chemistry. — [Expert | Proficient | Familiar | Aware | None]
- fam_particle_physics — Familiarity: Particle physics — How well the persona knows Particle physics. — [Expert | Proficient | Familiar | Aware | None]
- fam_astrophysics — Familiarity: Astrophysics — How well the persona knows Astrophysics. — [Expert | Proficient | Familiar | Aware | None]
- fam_astronomy — Familiarity: Astronomy — How well the persona knows Astronomy. — [Expert | Proficient | Familiar | Aware | None]
- fam_geology — Familiarity: Geology — How well the persona knows Geology. — [Expert | Proficient | Familiar | Aware | None]
- fam_oceanography — Familiarity: Oceanography — How well the persona knows Oceanography. — [Expert | Proficient | Familiar | Aware | None]
- fam_climate_science — Familiarity: Climate science — How well the persona knows Climate science. — [Expert | Proficient | Familiar | Aware | None]
- fam_ecology — Familiarity: Ecology — How well the persona knows Ecology. — [Expert | Proficient | Familiar | Aware | None]
- fam_sociology — Familiarity: Sociology — How well the persona knows Sociology. — [Expert | Proficient | Familiar | Aware | None]
- fam_psychology — Familiarity: Psychology — How well the persona knows Psychology. — [Expert | Proficient | Familiar | Aware | None]
- fam_cognitive_science — Familiarity: Cognitive science — How well the persona knows Cognitive science. — [Expert | Proficient | Familiar | Aware | None]
- fam_anthropology — Familiarity: Anthropology — How well the persona knows Anthropology. — [Expert | Proficient | Familiar | Aware | None]
- fam_international_relations — Familiarity: International relations — How well the persona knows International relations. — [Expert | Proficient | Familiar | Aware | None]
- fam_comparative_literature — Familiarity: Comparative literature — How well the persona knows Comparative literature. — [Expert | Proficient | Familiar | Aware | None]
- fam_philosophy — Familiarity: Philosophy — How well the persona knows Philosophy. — [Expert | Proficient | Familiar | Aware | None]
- fam_ethics — Familiarity: Ethics — How well the persona knows Ethics. — [Expert | Proficient | Familiar | Aware | None]
- fam_history — Familiarity: History — How well the persona knows History. — [Expert | Proficient | Familiar | Aware | None]
- fam_archaeology — Familiarity: Archaeology — How well the persona knows Archaeology. — [Expert | Proficient | Familiar | Aware | None]
- fam_linguistics — Familiarity: Linguistics — How well the persona knows Linguistics. — [Expert | Proficient | Familiar | Aware | None]
- fam_art_history — Familiarity: Art history — How well the persona knows Art history. — [Expert | Proficient | Familiar | Aware | None]
- fam_music_theory — Familiarity: Music theory — How well the persona knows Music theory. — [Expert | Proficient | Familiar | Aware | None]
- fam_film_studies — Familiarity: Film studies — How well the persona knows Film studies. — [Expert | Proficient | Familiar | Aware | None]
- fam_architecture — Familiarity: Architecture — How well the persona knows Architecture. — [Expert | Proficient | Familiar | Aware | None]
- fam_urban_planning — Familiarity: Urban planning — How well the persona knows Urban planning. — [Expert | Proficient | Familiar | Aware | None]
- fam_landscape_design — Familiarity: Landscape design — How well the persona knows Landscape design. — [Expert | Proficient | Familiar | Aware | None]
- fam_agronomy — Familiarity: Agronomy — How well the persona knows Agronomy. — [Expert | Proficient | Familiar | Aware | None]
- fam_horticulture — Familiarity: Horticulture — How well the persona knows Horticulture. — [Expert | Proficient | Familiar | Aware | None]
- fam_veterinary_medicine — Familiarity: Veterinary medicine — How well the persona knows Veterinary medicine. — [Expert | Proficient | Familiar | Aware | None]
- fam_nursing — Familiarity: Nursing — How well the persona knows Nursing. — [Expert | Proficient | Familiar | Aware | None]
- fam_pharmacology — Familiarity: Pharmacology — How well the persona knows Pharmacology. — [Expert | Proficient | Familiar | Aware | None]
- fam_public_health — Familiarity: Public health — How well the persona knows Public health. — [Expert | Proficient | Familiar | Aware | None]
- fam_epidemiology — Familiarity: Epidemiology — How well the persona knows Epidemiology. — [Expert | Proficient | Familiar | Aware | None]
- fam_nutrition — Familiarity: Nutrition — How well the persona knows Nutrition. — [Expert | Proficient | Familiar | Aware | None]
- fam_sports_science — Familiarity: Sports science — How well the persona knows Sports science. — [Expert | Proficient | Familiar | Aware | None]
- fam_cybersecurity — Familiarity: Cybersecurity — How well the persona knows Cybersecurity. — [Expert | Proficient | Familiar | Aware | None]
- fam_cryptography — Familiarity: Cryptography — How well the persona knows Cryptography. — [Expert | Proficient | Familiar | Aware | None]
- fam_computer_networking — Familiarity: Computer networking — How well the persona knows Computer networking. — [Expert | Proficient | Familiar | Aware | None]
- fam_databases — Familiarity: Databases — How well the persona knows Databases. — [Expert | Proficient | Familiar | Aware | None]
- fam_distributed_systems — Familiarity: Distributed systems — How well the persona knows Distributed systems. — [Expert | Proficient | Familiar | Aware | None]
- fam_operating_systems — Familiarity: Operating systems — How well the persona knows Operating systems. — [Expert | Proficient | Familiar | Aware | None]
- fam_compilers — Familiarity: Compilers — How well the persona knows Compilers. — [Expert | Proficient | Familiar | Aware | None]
- fam_cloud_infrastructure — Familiarity: Cloud infrastructure — How well the persona knows Cloud infrastructure. — [Expert | Proficient | Familiar | Aware | None]
- fam_devops — Familiarity: DevOps — How well the persona knows DevOps. — [Expert | Proficient | Familiar | Aware | None]
- fam_game_development — Familiarity: Game development — How well the persona knows Game development. — [Expert | Proficient | Familiar | Aware | None]
- fam_computer_graphics — Familiarity: Computer graphics — How well the persona knows Computer graphics. — [Expert | Proficient | Familiar | Aware | None]
- fam_computer_vision — Familiarity: Computer vision — How well the persona knows Computer vision. — [Expert | Proficient | Familiar | Aware | None]
- fam_natural_language_processing — Familiarity: Natural language processing — How well the persona knows Natural language processing. — [Expert | Proficient | Familiar | Aware | None]
- fam_human_computer_interaction — Familiarity: Human-computer interaction — How well the persona knows Human-computer interaction. — [Expert | Proficient | Familiar | Aware | None]
- fam_ux_research — Familiarity: UX research — How well the persona knows UX research. — [Expert | Proficient | Familiar | Aware | None]
- fam_graphic_design — Familiarity: Graphic design — How well the persona knows Graphic design. — [Expert | Proficient | Familiar | Aware | None]
- fam_industrial_design — Familiarity: Industrial design — How well the persona knows Industrial design. — [Expert | Proficient | Familiar | Aware | None]
- fam_typography — Familiarity: Typography — How well the persona knows Typography. — [Expert | Proficient | Familiar | Aware | None]
- fam_journalism — Familiarity: Journalism — How well the persona knows Journalism. — [Expert | Proficient | Familiar | Aware | None]
- fam_public_relations — Familiarity: Public relations — How well the persona knows Public relations. — [Expert | Proficient | Familiar | Aware | None]
- fam_brand_marketing — Familiarity: Brand marketing — How well the persona knows Brand marketing. — [Expert | Proficient | Familiar | Aware | None]
- fam_performance_marketing — Familiarity: Performance marketing — How well the persona knows Performance marketing. — [Expert | Proficient | Familiar | Aware | None]
- fam_seo — Familiarity: SEO — How well the persona knows SEO. — [Expert | Proficient | Familiar | Aware | None]
- fam_sales_engineering — Familiarity: Sales engineering — How well the persona knows Sales engineering. — [Expert | Proficient | Familiar | Aware | None]
- fam_supply_chain — Familiarity: Supply chain — How well the persona knows Supply chain. — [Expert | Proficient | Familiar | Aware | None]
- fam_logistics — Familiarity: Logistics — How well the persona knows Logistics. — [Expert | Proficient | Familiar | Aware | None]
- fam_operations_management — Familiarity: Operations management — How well the persona knows Operations management. — [Expert | Proficient | Familiar | Aware | None]
- fam_lean_manufacturing — Familiarity: Lean manufacturing — How well the persona knows Lean manufacturing. — [Expert | Proficient | Familiar | Aware | None]
- fam_quality_assurance — Familiarity: Quality assurance — How well the persona knows Quality assurance. — [Expert | Proficient | Familiar | Aware | None]
- fam_human_resources — Familiarity: Human resources — How well the persona knows Human resources. — [Expert | Proficient | Familiar | Aware | None]
- fam_organizational_psychology — Familiarity: Organizational psychology — How well the persona knows Organizational psychology. — [Expert | Proficient | Familiar | Aware | None]
- fam_project_management — Familiarity: Project management — How well the persona knows Project management. — [Expert | Proficient | Familiar | Aware | None]
- fam_product_management — Familiarity: Product management — How well the persona knows Product management. — [Expert | Proficient | Familiar | Aware | None]
- fam_venture_capital — Familiarity: Venture capital — How well the persona knows Venture capital. — [Expert | Proficient | Familiar | Aware | None]
- fam_private_equity — Familiarity: Private equity — How well the persona knows Private equity. — [Expert | Proficient | Familiar | Aware | None]
- fam_real_estate — Familiarity: Real estate — How well the persona knows Real estate. — [Expert | Proficient | Familiar | Aware | None]
- fam_insurance — Familiarity: Insurance — How well the persona knows Insurance. — [Expert | Proficient | Familiar | Aware | None]
- fam_actuarial_science — Familiarity: Actuarial science — How well the persona knows Actuarial science. — [Expert | Proficient | Familiar | Aware | None]
- fam_hospitality_management — Familiarity: Hospitality management — How well the persona knows Hospitality management. — [Expert | Proficient | Familiar | Aware | None]
- fam_culinary_arts — Familiarity: Culinary arts — How well the persona knows Culinary arts. — [Expert | Proficient | Familiar | Aware | None]
- fam_sommelier_knowledge — Familiarity: Sommelier knowledge — How well the persona knows Sommelier knowledge. — [Expert | Proficient | Familiar | Aware | None]
- fam_fashion_design — Familiarity: Fashion design — How well the persona knows Fashion design. — [Expert | Proficient | Familiar | Aware | None]
- fam_textiles — Familiarity: Textiles — How well the persona knows Textiles. — [Expert | Proficient | Familiar | Aware | None]
- fam_photography — Familiarity: Photography — How well the persona knows Photography. — [Expert | Proficient | Familiar | Aware | None]
- fam_cinematography — Familiarity: Cinematography — How well the persona knows Cinematography. — [Expert | Proficient | Familiar | Aware | None]
- fam_music_production — Familiarity: Music production — How well the persona knows Music production. — [Expert | Proficient | Familiar | Aware | None]
- fam_sound_engineering — Familiarity: Sound engineering — How well the persona knows Sound engineering. — [Expert | Proficient | Familiar | Aware | None]
- fam_animation — Familiarity: Animation — How well the persona knows Animation. — [Expert | Proficient | Familiar | Aware | None]
- fam_3d_modeling — Familiarity: 3D modeling — How well the persona knows 3D modeling. — [Expert | Proficient | Familiar | Aware | None]
- fam_geographic_information_systems — Familiarity: Geographic information systems — How well the persona knows Geographic information systems. — [Expert | Proficient | Familiar | Aware | None]
- fam_meteorology — Familiarity: Meteorology — How well the persona knows Meteorology. — [Expert | Proficient | Familiar | Aware | None]
- fam_forestry — Familiarity: Forestry — How well the persona knows Forestry. — [Expert | Proficient | Familiar | Aware | None]
- fam_marine_biology — Familiarity: Marine biology — How well the persona knows Marine biology. — [Expert | Proficient | Familiar | Aware | None]
- fam_paleontology — Familiarity: Paleontology — How well the persona knows Paleontology. — [Expert | Proficient | Familiar | Aware | None]
- fam_materials_science — Familiarity: Materials science — How well the persona knows Materials science. — [Expert | Proficient | Familiar | Aware | None]
- fam_nanotechnology — Familiarity: Nanotechnology — How well the persona knows Nanotechnology. — [Expert | Proficient | Familiar | Aware | None]
- fam_renewable_energy — Familiarity: Renewable energy — How well the persona knows Renewable energy. — [Expert | Proficient | Familiar | Aware | None]
- fam_nuclear_engineering — Familiarity: Nuclear engineering — How well the persona knows Nuclear engineering. — [Expert | Proficient | Familiar | Aware | None]
- fam_petroleum_engineering — Familiarity: Petroleum engineering — How well the persona knows Petroleum engineering. — [Expert | Proficient | Familiar | Aware | None]
- fam_mining — Familiarity: Mining — How well the persona knows Mining. — [Expert | Proficient | Familiar | Aware | None]
- fam_aviation — Familiarity: Aviation — How well the persona knows Aviation. — [Expert | Proficient | Familiar | Aware | None]
- fam_maritime_navigation — Familiarity: Maritime navigation — How well the persona knows Maritime navigation. — [Expert | Proficient | Familiar | Aware | None]
- fam_military_strategy — Familiarity: Military strategy — How well the persona knows Military strategy. — [Expert | Proficient | Familiar | Aware | None]
- fam_diplomacy — Familiarity: Diplomacy — How well the persona knows Diplomacy. — [Expert | Proficient | Familiar | Aware | None]
- fam_social_work — Familiarity: Social work — How well the persona knows Social work. — [Expert | Proficient | Familiar | Aware | None]
- fam_counseling — Familiarity: Counseling — How well the persona knows Counseling. — [Expert | Proficient | Familiar | Aware | None]
- fam_theology — Familiarity: Theology — How well the persona knows Theology. — [Expert | Proficient | Familiar | Aware | None]
- fam_library_science — Familiarity: Library science — How well the persona knows Library science. — [Expert | Proficient | Familiar | Aware | None]

INPUT:

{{input_json}}
