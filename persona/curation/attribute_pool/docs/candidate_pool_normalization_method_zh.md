# Candidate Pool Normalization 方法说明

最后更新：2026-06-19

## 目的

本文档说明 persona attribute candidate pool 的 Step 2 normalization 方法。

Step 2 的输入是 Step 1 生成的 raw extended candidate pool。它的任务是把不同来源、不同格式的候选 attribute 转换成统一、可审阅、可比较的 schema。

注意：Step 2 不做去重。

Step 2 的目标是让每条 candidate 更容易在后续步骤中进行：

- 比较；
- deduplication；
- categorization；
- source grounding；
- graph relation construction。

Normalization 的代码在：

- `normalize_candidate_pool.py`

输出文件在：

- `candidate_pool_outputs/normalized/candidate_pool_raw_extended_normalized.csv`
- `candidate_pool_outputs/normalized/candidate_pool_high_quality_normalized.csv`
- `candidate_pool_outputs/normalized/normalization_report.md`
- `candidate_pool_outputs/normalized/normalization_source_summary.csv`

ACS support files 由下面这些文件生成和保存：

- `build_acs_curated_variables.py`
- `dataset/acs_pums/PUMS_Data_Dictionary_2024.csv`
- `dataset/acs_pums/acs_pums_curated_variables.csv`

## 输入文件

脚本读取：

- `candidate_pool_outputs/candidate_pool_raw_extended.csv`
- `candidate_pool_outputs/candidate_pool_high_quality.csv`

其中：

- raw extended 文件包含 Step 1 收集到的所有 candidates；
- high-quality 文件包含主审阅池，也就是质量较高、优先处理的 subset。

## 输出原则

Normalization 保留每一行输入，不合并任何 candidate。

每条 candidate 会新增一组 normalized fields：

- canonical label 和 canonical name；
- normalized top-level category；
- normalized subcategory；
- inferred data type；
- measurement level；
- source family；
- quality tier；
- license risk；
- deduplication keys；
- aliases；
- review flags；
- application relevance。

这样 Step 3 做 dedup 和 graph 时，就不用直接面对各种来源里混乱的字段名和分类。

## 为什么先 Normalize，再 Dedup

不同 sources 经常用不同方式表达相似概念。

例子：

- `political_leaning`、`political_orientation`、`party_affiliation` 相关，但不一定等价。
- `risk_aversion`、`risk_tolerance`、`sensation_seeking` 都和 risk 有关，但不是同一个心理 construct。
- `openness`、`curiosity`、`intellectual_curiosity`、`need_for_cognition` 概念有交叉，但来自不同理论和量表体系。

Normalization 的作用是先把这些 candidate 转成可比较格式，但保留原始 source 差异。

也就是说：

- Normalize 让它们可以被比较；
- Dedup 决定它们是否应该合并；
- Graph 决定它们之间是什么关系。

## 新增 Normalized Fields

### `canonical_label`

清理后的 source label。

处理包括：

- 去掉重复后缀，例如 `.1`；
- 尽量修正编码 artifacts；
- 保留人类可读的 wording。

### `canonical_name`

从 `canonical_label` 生成的 snake_case 机器可读名称。

例子：

- `Political Orientation` -> `political_orientation`

### `normalized_primary_category`

修正后的一级分类，使用我们当前的 10-category persona schema：

1. Demographics & Population Grounding
2. Life Context & Constraints
3. Personality Traits
4. Values, Goals & Motivations
5. Worldview, Beliefs & Attitudes
6. Cognitive & Capability Profile
7. Behavioral Patterns & Preferences
8. Social Identity, Relationships & Community
9. Narrative Identity & Life History
10. Domain-Specific Overlays

### `normalized_subcategory`

清理后的二级分类，并且会考虑 source-specific 规则。

例子：

- `Facet MAP personality facets`
- `IPIP personality items`
- `Schwartz values`
- `sociodemographic attitudes`
- `domain labels and expertise areas`
- `hobbies interests and lifestyle`

### `normalized_definition`

标准化后的定义。

如果 source 已经提供了有用 definition，就保留 source definition。否则脚本会根据 label、category 和 subcategory 生成一个轻量 definition。

### `normalized_data_type`

推断出的数据类型。

常见取值包括：

- `likert_self_report_item`
- `psychometric_construct`
- `theory_construct`
- `ordinal_survey_item`
- `ordinal_or_binary_survey_item`
- `categorical`
- `multi_select`
- `free_text`
- `dataset_schema_field`
- `domain_label`
- `unknown_or_source_defined`

### `measurement_level`

更粗粒度的测量类型：

- `nominal`
- `ordinal`
- `construct`
- `free_text`
- `source_defined`

### `normalized_value_schema_json`

用 JSON 记录 value structure。

例如，IPIP items 会被标准化为 Likert-style self-report items，并带有标准 accuracy/agreement scale。

如果 official survey variable 没有直接抓到 value labels，就先标成 source-defined，并加 review flag，后续可以查 codebook。

### `source_family`

更高层的 source 分组：

- `psychometric`
- `official_population_survey`
- `official_survey`
- `research_dataset`
- `persona_dataset`
- `llm_mined`
- `local_project`
- `validated_theory`
- `other`

### `quality_tier`

从 Step 1 的 inclusion tier 推导：

- `A`：validated psychometric scale、official survey variable 或 theory construct；
- `B`：peer-reviewed dataset、curated local schema 或 dataset field；
- `C`：LLM-mined 或自动抽取，需要 review。

### `license_risk`

粗略的 downstream reuse 风险标记：

- `low`
- `medium`
- `medium_high`
- `unknown`

这不是法律意见，只是提醒我们后续整理和发布时要检查 license。

### `dedup_key_strict`

严格 dedup key，由 normalized category 和 canonical label 构成。

适合检测 exact duplicate 或 near-exact duplicate。

### `dedup_key_loose`

宽松 dedup key。

它会移除常见 stopwords，并对核心 tokens 排序。适合发现可能重复、但需要人工或 semantic review 的候选 clusters。

### `alias_candidates_json`

可能的 aliases，来自：

- original label；
- source-provided name；
- original source ID；
- canonical name。

### `review_flags_json`

标记为什么这条 candidate 需要特殊审阅。

常见 flags：

- `review_low_evidence_or_llm_mined`
- `review_deeppersona_auto_extraction`
- `domain_label_not_standalone_attribute`
- `domain_specific_not_core_by_default`
- `needs_value_schema_or_codebook_lookup`
- `auto_augmented_values_review`
- `label_too_generic_review`
- `free_text_should_be_structured_before_final_schema`

### `needs_review`

如果有任何 review flags，则为 true。

### Boolean Helper Fields

脚本还会生成：

- `is_questionnaire_item`
- `is_construct`
- `is_dataset_field`
- `is_domain_label`
- `is_generated_or_mined`

这些字段方便筛选。

### `application_relevance`

粗略标记该 candidate 可能服务的应用方向。

例子：

- `general_personality_and_behavior_simulation`
- `survey_social_science_policy_and_alignment`
- `motivation_preference_and_decision_simulation`
- `education_workflow_task_capability_simulation`
- `recommender_consumer_media_and_daily_behavior`
- `population_grounding_sampling_and_fairness_analysis`
- `domain_specific_module_selection`

## Source-Specific Normalization Rules

### Psychometric Sources

来源：

- IPIP
- Facet MAP
- BFI-2
- HEXACO

规则：

- 默认映射到 `Personality Traits`；
- 保留 psychometric source 的原始名称；
- IPIP items 推断为 `likert_self_report_item`；
- scales、facets、domains 推断为 `psychometric_construct`；
- validated 或 public-domain psychometric material 默认 quality 较高。

例外：

- `Need for Cognition` 可视为 cognitive style，Step 3 中可以和 personality 建 cross-link。

### Values and Motivation Sources

来源：

- Schwartz Theory of Basic Values
- Self-Determination Theory

规则：

- 映射到 `Values, Goals & Motivations`；
- 推断为 `theory_construct`；
- 保留 high evidence level。

### Official Survey Sources

来源：

- ACS PUMS curated variables
- GSS
- WVS

规则：

- ACS 作为 official population-grounding layer 使用，不把它当成行为决定因素；
- ACS variables 映射到 demographics、life context、capability、social/family context；
- ACS fields 会被标准化为 `official_population_numeric_variable`、`official_population_categorical_variable`、`official_population_binary_variable` 或 `official_population_ordinal_variable`；
- 根据 survey sections 和关键词映射到我们的 10-category schema；
- 尽可能推断 survey item type；
- 没有 value labels 的变量加 `needs_value_schema_or_codebook_lookup`；
- 保留 source ID 和 raw category path，方便后续 grounding。

### Research Datasets

来源：

- Apple ML-PrimeX

规则：

- worldview / opinion questions 映射到 `Worldview, Beliefs & Attitudes`；
- PI-18 Primal World Beliefs items 映射到 `primal world beliefs`；
- explanation fields 标为 belief explanations；
- 因为 PrimeX 有 non-commercial / no-derivatives license，需要保留 license risk。

### Persona Dataset Sources

来源：

- SCOPE-Persona
- Nemotron-Personas-USA
- OASIS

规则：

- SCOPE facets 映射到相应理论 category；
- Nemotron demographic/geographic fields 映射到 population grounding；
- Nemotron skills 映射到 capability；
- Nemotron hobbies/sports/arts/travel/culinary fields 映射到 behavioral preferences；
- OASIS 的 MBTI 映射到 personality traits，profession 映射到 domain overlay，interested topics 映射到 behavioral preferences。

### DeepPersona Auto-Extractions

规则：

- 使用 DeepPersona top-level categories 作为 subcategory hints；
- 将其重新映射到我们的 10-category schema；
- 所有 DeepPersona auto-extracted attributes 都加 review flags；
- 在没有进一步 grounding 前，不把它们当作 high-quality final attributes。

例子：

- `Media Preferences` -> `Behavioral Patterns & Preferences`
- `Analytical Skills` -> `Cognitive & Capability Profile`
- `Sensitivity` -> `Personality Traits`
- `Guidance` -> `Social Identity, Relationships & Community`

### PersonaHub Domain Labels

规则：

- 所有 sampled PersonaHub domain labels 统一映射到 `Domain-Specific Overlays`；
- 推断为 `domain_label`；
- 加 `domain_label_not_standalone_attribute` flag；
- 在转换成 domain modules 或 expertise attributes 前，不把它们当作 standalone persona attributes。

例子：

- `Aerospace Engineering` 本身不是通用 persona attribute。它更像 domain / expertise label，可以支持未来的 professional module 或 domain-specific module。

## Review Philosophy

Normalization 是保守的。

它不会假设相似词就是同一个 construct。

例如：

- `risk_aversion`
- `risk_tolerance`
- `sensation_seeking`

这三个应该在 graph 里建立关系，但不应该自动合并。

原因是它们共享 risk 主题，但测量的是不同机制：

- 对不确定性的回避；
- 对损失或波动的承受能力；
- 对刺激和新奇体验的追求。

Step 3 应该建立类似关系：

- `negatively_correlates_with`
- `related_to`
- `domain_specific_to`

但不应该把它们直接压成一个泛泛的 `risk_preference`。

## Step 2 QA Checks

Normalization 脚本会检查：

- 行数是否保留；
- candidate ID 是否重复；
- canonical label 是否为空；
- normalized category 是否都落在 10 类里；
- 从 Step 1 到 Step 2 有多少 category 被修正；
- data type counts；
- review flag counts。

当前输出：

- raw extended normalized rows：28,463；
- high-quality normalized rows：9,935；
- duplicate candidate IDs：0；
- empty canonical labels：0；
- unknown normalized categories：0。

## 下一步

Step 3 应该使用 normalized outputs 来做：

- exact duplicate detection；
- loose duplicate clustering；
- alias consolidation；
- source priority selection；
- relation graph construction；
- final category/subcategory review。

Step 3 最重要的输入字段是：

- `dedup_key_strict`
- `dedup_key_loose`
- `canonical_name`
- `normalized_primary_category`
- `normalized_subcategory`
- `source_family`
- `quality_tier`
- `review_flags_json`
