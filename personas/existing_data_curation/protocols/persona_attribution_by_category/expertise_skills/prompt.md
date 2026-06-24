You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Expertise: Skills  (64 dimensions)

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
- skill_writing — Skill: Writing — Proficiency in writing. — [Master | Advanced | Intermediate | Beginner | None]
- skill_copywriting — Skill: Copywriting — Proficiency in copywriting. — [Master | Advanced | Intermediate | Beginner | None]
- skill_editing — Skill: Editing — Proficiency in editing. — [Master | Advanced | Intermediate | Beginner | None]
- skill_storytelling — Skill: Storytelling — Proficiency in storytelling. — [Master | Advanced | Intermediate | Beginner | None]
- skill_public_speaking — Skill: Public speaking — Proficiency in public speaking. — [Master | Advanced | Intermediate | Beginner | None]
- skill_negotiation — Skill: Negotiation — Proficiency in negotiation. — [Master | Advanced | Intermediate | Beginner | None]
- skill_coding — Skill: Coding — Proficiency in coding. — [Master | Advanced | Intermediate | Beginner | None]
- skill_debugging — Skill: Debugging — Proficiency in debugging. — [Master | Advanced | Intermediate | Beginner | None]
- skill_code_review — Skill: Code review — Proficiency in code review. — [Master | Advanced | Intermediate | Beginner | None]
- skill_system_design — Skill: System design — Proficiency in system design. — [Master | Advanced | Intermediate | Beginner | None]
- skill_data_analysis — Skill: Data analysis — Proficiency in data analysis. — [Master | Advanced | Intermediate | Beginner | None]
- skill_data_visualization — Skill: Data visualization — Proficiency in data visualization. — [Master | Advanced | Intermediate | Beginner | None]
- skill_statistical_modeling — Skill: Statistical modeling — Proficiency in statistical modeling. — [Master | Advanced | Intermediate | Beginner | None]
- skill_spreadsheet_modeling — Skill: Spreadsheet modeling — Proficiency in spreadsheet modeling. — [Master | Advanced | Intermediate | Beginner | None]
- skill_financial_modeling — Skill: Financial modeling — Proficiency in financial modeling. — [Master | Advanced | Intermediate | Beginner | None]
- skill_project_management — Skill: Project management — Proficiency in project management. — [Master | Advanced | Intermediate | Beginner | None]
- skill_product_strategy — Skill: Product strategy — Proficiency in product strategy. — [Master | Advanced | Intermediate | Beginner | None]
- skill_leadership — Skill: Leadership — Proficiency in leadership. — [Master | Advanced | Intermediate | Beginner | None]
- skill_people_management — Skill: People management — Proficiency in people management. — [Master | Advanced | Intermediate | Beginner | None]
- skill_mentoring — Skill: Mentoring — Proficiency in mentoring. — [Master | Advanced | Intermediate | Beginner | None]
- skill_coaching — Skill: Coaching — Proficiency in coaching. — [Master | Advanced | Intermediate | Beginner | None]
- skill_conflict_resolution — Skill: Conflict resolution — Proficiency in conflict resolution. — [Master | Advanced | Intermediate | Beginner | None]
- skill_time_management — Skill: Time management — Proficiency in time management. — [Master | Advanced | Intermediate | Beginner | None]
- skill_prioritization — Skill: Prioritization — Proficiency in prioritization. — [Master | Advanced | Intermediate | Beginner | None]
- skill_research — Skill: Research — Proficiency in research. — [Master | Advanced | Intermediate | Beginner | None]
- skill_critical_thinking — Skill: Critical thinking — Proficiency in critical thinking. — [Master | Advanced | Intermediate | Beginner | None]
- skill_problem_solving — Skill: Problem solving — Proficiency in problem solving. — [Master | Advanced | Intermediate | Beginner | None]
- skill_mathematics — Skill: Mathematics — Proficiency in mathematics. — [Master | Advanced | Intermediate | Beginner | None]
- skill_mental_arithmetic — Skill: Mental arithmetic — Proficiency in mental arithmetic. — [Master | Advanced | Intermediate | Beginner | None]
- skill_logical_reasoning — Skill: Logical reasoning — Proficiency in logical reasoning. — [Master | Advanced | Intermediate | Beginner | None]
- skill_language_learning — Skill: Language learning — Proficiency in language learning. — [Master | Advanced | Intermediate | Beginner | None]
- skill_translation — Skill: Translation — Proficiency in translation. — [Master | Advanced | Intermediate | Beginner | None]
- skill_interpretation — Skill: Interpretation — Proficiency in interpretation. — [Master | Advanced | Intermediate | Beginner | None]
- skill_design_thinking — Skill: Design thinking — Proficiency in design thinking. — [Master | Advanced | Intermediate | Beginner | None]
- skill_prototyping — Skill: Prototyping — Proficiency in prototyping. — [Master | Advanced | Intermediate | Beginner | None]
- skill_sketching — Skill: Sketching — Proficiency in sketching. — [Master | Advanced | Intermediate | Beginner | None]
- skill_drawing — Skill: Drawing — Proficiency in drawing. — [Master | Advanced | Intermediate | Beginner | None]
- skill_painting — Skill: Painting — Proficiency in painting. — [Master | Advanced | Intermediate | Beginner | None]
- skill_photography — Skill: Photography — Proficiency in photography. — [Master | Advanced | Intermediate | Beginner | None]
- skill_videography — Skill: Videography — Proficiency in videography. — [Master | Advanced | Intermediate | Beginner | None]
- skill_video_editing — Skill: Video editing — Proficiency in video editing. — [Master | Advanced | Intermediate | Beginner | None]
- skill_audio_production — Skill: Audio production — Proficiency in audio production. — [Master | Advanced | Intermediate | Beginner | None]
- skill_cooking — Skill: Cooking — Proficiency in cooking. — [Master | Advanced | Intermediate | Beginner | None]
- skill_baking — Skill: Baking — Proficiency in baking. — [Master | Advanced | Intermediate | Beginner | None]
- skill_budgeting — Skill: Budgeting — Proficiency in budgeting. — [Master | Advanced | Intermediate | Beginner | None]
- skill_investing — Skill: Investing — Proficiency in investing. — [Master | Advanced | Intermediate | Beginner | None]
- skill_diy_repair — Skill: DIY repair — Proficiency in diy repair. — [Master | Advanced | Intermediate | Beginner | None]
- skill_gardening — Skill: Gardening — Proficiency in gardening. — [Master | Advanced | Intermediate | Beginner | None]
- skill_driving — Skill: Driving — Proficiency in driving. — [Master | Advanced | Intermediate | Beginner | None]
- skill_technical_writing — Skill: Technical writing — Proficiency in technical writing. — [Master | Advanced | Intermediate | Beginner | None]
- skill_note_taking — Skill: Note-taking — Proficiency in note-taking. — [Master | Advanced | Intermediate | Beginner | None]
- skill_speed_reading — Skill: Speed reading — Proficiency in speed reading. — [Master | Advanced | Intermediate | Beginner | None]
- skill_memorization — Skill: Memorization — Proficiency in memorization. — [Master | Advanced | Intermediate | Beginner | None]
- skill_active_listening — Skill: Active listening — Proficiency in active listening. — [Master | Advanced | Intermediate | Beginner | None]
- skill_empathy — Skill: Empathy — Proficiency in empathy. — [Master | Advanced | Intermediate | Beginner | None]
- skill_persuasion — Skill: Persuasion — Proficiency in persuasion. — [Master | Advanced | Intermediate | Beginner | None]
- skill_facilitation — Skill: Facilitation — Proficiency in facilitation. — [Master | Advanced | Intermediate | Beginner | None]
- skill_forecasting — Skill: Forecasting — Proficiency in forecasting. — [Master | Advanced | Intermediate | Beginner | None]
- skill_estimation — Skill: Estimation — Proficiency in estimation. — [Master | Advanced | Intermediate | Beginner | None]
- skill_fact_checking — Skill: Fact-checking — Proficiency in fact-checking. — [Master | Advanced | Intermediate | Beginner | None]
- skill_proofreading — Skill: Proofreading — Proficiency in proofreading. — [Master | Advanced | Intermediate | Beginner | None]
- skill_presenting — Skill: Presenting — Proficiency in presenting. — [Master | Advanced | Intermediate | Beginner | None]
- skill_networking — Skill: Networking — Proficiency in networking. — [Master | Advanced | Intermediate | Beginner | None]
- skill_selling — Skill: Selling — Proficiency in selling. — [Master | Advanced | Intermediate | Beginner | None]

INPUT:

{{input_json}}
