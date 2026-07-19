# Industry-Related Persona Attributes

This note maps common MatrAIx application domains to persona schema attributes
that are useful for cohort selection, scenario design, and coverage checks.

Source: migrated from MatrAIx PR `#74`,
`personas/Relevant Persona Attributes by Industry.md`.

## English

### Movie And Entertainment

Domain: commerce and retail.

Attributes:

- `fam_film_studies`, `fam_cinematography`, `topic_film`,
  `topic_tv_series`, `lstyle_streaming_hours`, `ind_entertainment`
- `filmg_action`, `filmg_adventure`, `filmg_comedy`, `filmg_drama`,
  `filmg_horror`, `filmg_thriller`, `filmg_sci_fi`, `filmg_fantasy`,
  `filmg_romance`, `filmg_documentary`, `filmg_animation`, `filmg_crime`,
  `filmg_mystery`, `filmg_historical`, `filmg_war`, `filmg_western`,
  `filmg_musical`, `filmg_noir`, `filmg_superhero`, `filmg_indie_film`,
  `filmg_art_house`, `filmg_biopic`, `filmg_comedy_drama`,
  `filmg_disaster`

Use for movie and TV interest, streaming habits, entertainment industry
experience, film/cinematography familiarity, and genre preferences.

### Beauty

Domain: commerce and retail.

Attributes:

- `ind_beauty_cosmetics`, `val_beauty_aesthetics`,
  `trait_appreciation_of_beauty`, `bfi2_facet_aesthetic_sensitivity`,
  `fam_fashion_design`, `topic_fashion`, `lstyle_fashion_sense`,
  `att_fast_fashion`

Use for beauty/cosmetics industry experience, aesthetic values, appreciation of
beauty, fashion interest, fashion sense, and attitude toward fast fashion.

### Games

Domain: commerce and retail.

Attributes:

- `fam_game_development`, `ind_gaming`, `topic_gaming`,
  `topic_board_games`, `lstyle_gaming_freq`, `sport_esports`

Use for game development familiarity, gaming industry experience, gaming and
board-game interest, gaming frequency, and esports participation or following.

### Finance

Attributes:

- `fam_corporate_finance`, `skill_financial_modeling`, `skill_budgeting`,
  `skill_investing`, `topic_personal_finance`, `topic_investing`,
  `habit_budget_tracking`
- `ind_finance`, `ind_banking`, `ind_insurance`, `lstyle_payment_pref`,
  `lstyle_banking_style`, `lstyle_investment_style`,
  `lifex_financial_trajectory`, `dospert_financial_risk_tolerance`

Use for finance knowledge and skills, personal finance/investing interests,
budgeting habits, finance/banking/insurance industry experience, payment,
banking, investment style, financial trajectory, and financial risk tolerance.

### Health

Attributes:

- `fam_public_health`, `acad_health_science`, `ind_healthcare`,
  `ind_fitness_wellness`, `topic_fitness`, `habit_stretching_mobility`,
  `val_health`, `lifex_health_journey`,
  `dospert_health_safety_risk_tolerance`
- `health_general_health`, `health_chronic_condition`, `health_mobility`,
  `health_vision`, `health_hearing`, `health_color_vision`,
  `health_dexterity`, `health_mental_health`, `health_stress_level`,
  `health_energy_level`, `health_sleep_quality`, `health_pain_level`,
  `health_medication_use`, `health_dietary_restriction`,
  `health_neurodivergence`, `health_caregiver_status`,
  `health_health_literacy`, `health_insurance_status`,
  `health_fitness_level`, `health_cognitive_load_capacity`,
  `health_contrast_need`, `health_text_size_need`, `health_assistive_tech`,
  `health_motion_sensitivity`, `health_attention_condition`

Use for public health familiarity, health science interest, healthcare/fitness
industry experience, fitness habits, health values, health journey, health and
safety risk tolerance, and physical, mental, accessibility, medication, sleep,
stress, pain, insurance, and health-literacy attributes.

### Coding

Attributes:

- `skill_coding`, `skill_code_review`, `code_comment_style`,
  `code_summary_documentation`, `code_naming_verbosity`,
  `code_indentation_style`, `code_structure_preference`,
  `code_function_length`, `code_error_handling`, `code_abstraction_level`,
  `code_dependencies_approach`, `code_performance_priority`,
  `code_testing_approach`, `code_refactoring_frequency`
- `prog_python`, `prog_javascript`, `prog_typescript`, `prog_java`,
  `prog_c`, `prog_go`, `prog_rust`, `prog_ruby`, `prog_php`, `prog_swift`,
  `prog_kotlin`, `prog_objective_c`, `prog_scala`, `prog_haskell`,
  `prog_elixir`, `prog_erlang`, `prog_clojure`, `prog_lua`, `prog_perl`,
  `prog_r`, `prog_julia`, `prog_matlab`, `prog_sql`, `prog_bash`,
  `prog_powershell`, `prog_dart`, `prog_f`, `prog_ocaml`, `prog_assembly`,
  `prog_cobol`, `prog_fortran`, `prog_solidity`, `prog_graphql`

Use for coding and code-review skills, programming style preferences,
testing/refactoring/error-handling preferences, and programming-language
proficiency.

## Chinese

中文部分翻译每个行业的用途说明；属性 ID 与上方 English 部分相同。

### 电影与娱乐

领域：商业与零售。

用途：电影/电视剧兴趣、流媒体观看习惯、娱乐行业经验、电影研究/摄影熟悉度，以及电影类型偏好。

### 美妆

领域：商业与零售。

用途：美妆/化妆品行业经验、审美价值观、对美的欣赏程度、时尚兴趣、时尚风格，以及对快时尚的态度。

### 游戏

领域：商业与零售。

用途：游戏开发熟悉度、游戏行业经验、电子游戏/桌游兴趣、游戏频率，以及电竞参与或关注程度。

### 金融

用途：金融知识与技能、个人理财/投资兴趣、预算记录习惯、金融/银行/保险行业经验、支付/银行/投资方式、财务轨迹，以及金融风险承受度。

### 健康

用途：公共健康熟悉度、健康科学兴趣、医疗/健身行业经验、健身习惯、健康价值观、个人健康经历、健康/安全风险承受度，以及身体、心理、无障碍、用药、睡眠、压力、疼痛、保险和健康素养等属性。

### 编程

用途：编码和代码审查能力、编程风格偏好、测试/重构/错误处理偏好，以及多种编程语言熟练度。
