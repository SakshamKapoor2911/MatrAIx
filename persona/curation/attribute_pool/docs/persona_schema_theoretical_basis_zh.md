# Persona Schema 的理论基础与属性构建计划

最后更新：2026-06-19

## 目的

本文档总结 MatrAIx persona attribute schema 当前的理论基础，并说明如何使用 SCOPE、DeepPersona、Nemotron、PrimeX、WVS、GSS、ACS PUMS、Big Five、HEXACO、Facet MAP、IPIP 等外部来源。

我们的目标不是尽可能多地收集 attributes，而是构建一个有理论支撑、面向 simulation 的 persona schema，使其能够支持：

- 真实感更强的 user / agent simulation；
- attribute 去重与 source grounding；
- attribute 之间的相关性与冲突分析；
- 面向不同应用场景的 domain-specific persona modules；
- 清楚说明每个 attribute 为什么应该进入候选池。

## 核心立场

我们的 top-level schema 不应该直接照搬 DeepPersona、SCOPE、Nemotron 或任何单一数据集。

相反：

- SCOPE 提供了近期 LLM-persona framework，并给出证据说明 demographic-only personas 是不充分的。
- DeepPersona 提供了广泛的长尾 attribute 覆盖，以及有用的 subcategory 粒度。
- Nemotron 提供了 demographic、geographic、occupation、skills、hobbies、cultural background、career goals 等方面的 grounding。
- PrimeX、WVS、GSS 提供了 worldview、belief、opinion、attitude 和社会科学 grounding。
- Big Five、HEXACO、Facet MAP、IPIP 提供了经过验证的人格 trait 和 facet 来源。

我们的 schema 应该使用一个综合性的理论架构，然后把每个外部 source 映射到这个架构中。

## 理论基础栈

### 1. McAdams 的人格三层理论

McAdams 的框架很适合作为“我们如何理解一个人”的高层架构。

它把人格分为：

- Level 1：dispositional traits，即稳定的人格特质；
- Level 2：characteristic adaptations，例如目标、价值观、应对策略、动机、角色、关系和习惯；
- Level 3：narrative identity，即一个人内化的人生故事，它给个人带来连续性和意义感。

映射到我们的 schema：

- `Personality Traits` 对应 dispositional traits。
- `Values, Goals & Motivations`、`Behavioral Patterns & Preferences`、`Social Identity, Relationships & Community` 对应 characteristic adaptations。
- `Narrative Identity & Life History` 对应 narrative identity。

为什么重要：

McAdams 给了我们一个很强的论证：persona 不应该只有 demographics 或 trait scores。一个真实的 persona 需要稳定 traits、与情境相关的 adaptations，以及 life narrative。

主要来源：

- McAdams, D. P. (1995). What Do We Know When We Know a Person? Journal of Personality. https://onlinelibrary.wiley.com/doi/10.1111/j.1467-6494.1995.tb00500.x
- McAdams, D. P., & Pals, J. L. (2006). A New Big Five: Fundamental Principles for an Integrative Science of Personality. https://pubmed.ncbi.nlm.nih.gov/16594837/

### 2. Trait Psychology：Big Five、HEXACO、Facet MAP 与 IPIP

Trait psychology 支撑 personality 层。

有用来源：

- Big Five / BFI-2：宽泛的五因素人格 domains，以及 15 个 facets。
- HEXACO：六因素模型，在 Big Five 基础上加入 Honesty-Humility 作为重要维度。
- Facet MAP：细粒度、开放访问的人格 facet taxonomy。
- IPIP：public-domain 的 personality items 和 scales 池。

映射到我们的 schema：

- `Personality Traits`
- `Cognitive & Capability Profile` 的一部分
- 作为 subcategory 的 `Emotional and Relational Skills` 的一部分

为什么重要：

这些 sources 为 personality attributes 提供了经过验证的名称、定义和 scales。我们应该用它们来避免凭空发明一些模糊 traits，例如没有测量 grounding 的 “nice” 或 “smart”。

来源：

- BFI-2: https://www.colby.edu/academics/departments-and-programs/psychology/research-opportunities/personality-lab/the-bfi-2/
- HEXACO: https://hexaco.org/
- Facet MAP: https://facetmap.org/facet-labels-and-definitions/
- IPIP: https://ipip.ori.org/

### 3. Values、Worldview、Beliefs 与 Attitudes

Values 和 beliefs 解释一个人为什么偏好某些选择、做出某些判断，或以某种方式回应社会情境。

有用来源：

- Schwartz Theory of Basic Human Values；
- World Values Survey (WVS)；
- General Social Survey (GSS)；
- PrimeX / Primal World Beliefs；
- Pew 风格的 public opinion 和 internet behavior surveys。

映射到我们的 schema：

- `Values, Goals & Motivations`
- `Worldview, Beliefs & Attitudes`
- `Behavioral Patterns & Preferences` 的一部分

为什么重要：

两个 demographics 类似、traits 也类似的人，仍然可能因为 values、worldview、moral priorities、political attitudes、religious beliefs 或 institutional trust 水平不同，而表现出不同的行为。

来源：

- Schwartz values overview: https://scholarworks.gvsu.edu/orpc/vol2/iss1/11/
- WVS: https://www.worldvaluessurvey.org/
- GSS: https://gss.norc.org/
- PrimeX: https://github.com/apple/ml-primex

### 4. Social Identity 与 Population Grounding

Demographics 不是行为决定因素，但它们作为 social position、lived context 和 structural constraint 很重要。

有用来源：

- Social Identity Theory；
- U.S. Census / ACS PUMS / IPUMS；
- Nemotron-Personas-USA；
- OASIS；
- population survey metadata。

映射到我们的 schema：

- `Demographics & Population Grounding`
- `Life Context & Constraints`
- `Social Identity, Relationships & Community`
- 作为 subcategory 的 `Cultural and Social Context`

为什么重要：

Age、gender、race / ethnicity、region、education、occupation、income、household structure、language、cultural background 应该作为 grounding variables 被纳入。但它们不应该被当作行为的简单 proxy。SCOPE 的发现尤其重要：demographic-only personas 可能放大 stereotypes，而且只能解释人类行为相似性中的一小部分。

来源：

- Social Identity Theory overview: https://www.simplypsychology.org/social-identity-theory.html
- Census ACS PUMS documentation: https://www.census.gov/programs-surveys/acs/microdata/documentation.html
- 2024 ACS PUMS documentation and data dictionary: https://www.census.gov/programs-surveys/acs/microdata/documentation/2024.html
- IPUMS: https://www.ipums.org/projects
- Nemotron-Personas-USA: https://huggingface.co/datasets/nvidia/Nemotron-Personas-USA

### 5. Person-Situation Interaction 与 Simulation Grounding

对于 simulation，persona attributes 不应该被当成会机械决定行为的静态标签。行为来自以下因素之间的交互：

- 稳定 dispositions；
- values 与 goals；
- life context；
- social role；
- prior experience；
- current environment；
- task framing；
- interaction history。

映射到我们的 schema：

- 所有 top-level categories；
- 尤其是 `Domain-Specific Overlays`；
- 未来的 interaction-state 或 environment-conditioned persona modules。

为什么重要：

这使我们能够区分 base persona attributes 和 task-specific overlays。例如，finance simulation 需要 risk tolerance、numeracy、financial stress、trust、time horizon；education simulation 需要 self-efficacy、learning style、motivation、prior knowledge 和 anxiety。

来源：

- SCOPE paper: https://arxiv.org/html/2601.07110v2
- SCOPE dataset: https://huggingface.co/datasets/Salesforce/SCOPE-Persona

## 建议的 Top-Level Schema

### 1. Demographics & Population Grounding

目的：

把 persona 连接到 population-level variables 和 social position。

示例 subcategories：

- age；
- gender；
- race / ethnicity；
- location；
- language；
- education level；
- household structure；
- citizenship / migration background；
- income bracket；
- occupation class。

主要 grounding：

- Census / ACS PUMS / IPUMS；
- Nemotron；
- OASIS；
- SCOPE demographic facet。

### 2. Life Context & Constraints

目的：

捕捉影响一个人能做什么的现实条件。

示例 subcategories：

- physical and health characteristics；
- financial constraints；
- time constraints；
- housing context；
- family / caregiving responsibilities；
- technology access；
- mobility constraints；
- work context；
- education context。

主要 grounding：

- DeepPersona physical / health category；
- Census / ACS；
- GSS；
- domain-specific surveys。

### 3. Personality Traits

目的：

捕捉稳定的心理 dispositions。

示例 subcategories：

- Big Five domains；
- HEXACO domains；
- selected Facet MAP facets；
- selected IPIP scales；
- emotional tendencies；
- interpersonal disposition。

主要 grounding：

- Big Five / BFI-2；
- HEXACO；
- Facet MAP；
- IPIP；
- SCOPE Big Five facet。

### 4. Values, Goals & Motivations

目的：

捕捉一个人在意什么，以及他们试图优化什么。

示例 subcategories：

- Schwartz values；
- life goals；
- achievement orientation；
- security orientation；
- autonomy；
- benevolence；
- tradition；
- self-direction；
- short-term and long-term goals。

主要 grounding：

- Schwartz values；
- SCOPE values facet；
- PrimeX；
- WVS / ESS。

### 5. Worldview, Beliefs & Attitudes

目的：

捕捉一个人对社会、制度、道德和世界的更广义理解。

示例 subcategories：

- political orientation；
- institutional trust；
- religiosity；
- moral beliefs；
- social issue attitudes；
- environmental concern；
- primal world beliefs；
- optimism / pessimism about society。

主要 grounding：

- WVS；
- GSS；
- PrimeX；
- Pew-style public opinion surveys。

### 6. Cognitive & Capability Profile

目的：

捕捉一个人知道什么、能做什么，以及如何处理信息。

示例 subcategories：

- domain expertise；
- literacy；
- numeracy；
- digital literacy；
- language proficiency；
- learning style；
- decision style；
- need for cognition；
- problem-solving style；
- communication skill。

主要 grounding：

- DeepPersona education / learning category；
- Nemotron skills；
- OECD PIAAC；
- CEFR；
- DigComp；
- IPIP / Facet MAP 中 selected cognitive styles。

### 7. Behavioral Patterns & Preferences

目的：

捕捉 routines、habits、tastes 和 repeated behavior。

示例 subcategories：

- hobbies and interests；
- lifestyle preferences；
- daily routine；
- media consumption；
- shopping behavior；
- travel preference；
- food / culinary preference；
- sports / fitness behavior；
- communication behavior；
- technology use。

主要 grounding：

- DeepPersona hobbies、lifestyle、routine、media categories；
- Nemotron sports / arts / travel / culinary / hobbies fields；
- SCOPE behavioral patterns facet；
- GSS / WVS behavior items。

### 8. Social Identity, Relationships & Community

目的：

捕捉塑造 identity 和 behavior 的 social groups、roles、relationships 和 communities。

示例 subcategories：

- cultural background；
- community belonging；
- family relationships；
- friendship network；
- workplace role；
- group identity；
- social network structure；
- civic participation。

主要 grounding：

- Social Identity Theory；
- DeepPersona cultural / relationship categories；
- Nemotron cultural background；
- GSS / WVS civic and social trust items；
- SCOPE sociodemographic behavior。

### 9. Narrative Identity & Life History

目的：

捕捉一个人的 self-story、formative experiences 和 meaning-making。

示例 subcategories：

- personal story；
- formative events；
- turning points；
- self-description；
- aspirations；
- life themes；
- identity change over time。

主要 grounding：

- McAdams narrative identity theory；
- SCOPE identity narratives；
- DeepPersona life story and background。

### 10. Domain-Specific Overlays

目的：

为具体 simulation tasks 添加必要 attributes，同时避免让 core schema 过度膨胀。

示例 modules：

- finance persona；
- health persona；
- education persona；
- recommender persona；
- political survey persona；
- workplace persona；
- media / social platform persona。

主要 grounding：

- domain-specific benchmarks；
- survey sources；
- task-specific literature；
- application requirements。

## DeepPersona Subcategory 映射

DeepPersona 的 12 个 top-level categories 适合作为 subcategory coverage 使用，但不适合作为我们的最终 top-level schema。

| DeepPersona category | 映射到我们的 schema | 备注 |
|---|---|---|
| Demographic Information | Demographics & Population Grounding | 直接对应。 |
| Physical and Health Characteristics | Life Context & Constraints; Domain-Specific Overlays | Health 应该是一个重要 subcategory，尤其适用于 health simulations。 |
| Psychological and Cognitive Aspects | Personality Traits; Cognitive & Capability Profile | 我们拆分 personality 和 cognition，因为它们的理论基础不同。 |
| Cultural and Social Context | Social Identity, Relationships & Community; Narrative Identity & Life History | 对 cultural grounding 和 lived context 很有用。 |
| Relationships and Social Networks | Social Identity, Relationships & Community | 直接对应。 |
| Career and Work Identity | Life Context & Constraints; Cognitive & Capability Profile; Domain-Specific Overlays | 可以发展为 professional identity submodule。 |
| Education and Learning | Demographics & Population Grounding; Cognitive & Capability Profile; Life Context & Constraints | Education 既是背景，也是 capability。 |
| Hobbies, Interests, and Lifestyle | Behavioral Patterns & Preferences | 直接对应。 |
| Lifestyle and Daily Routine | Behavioral Patterns & Preferences | 直接对应。 |
| Core Values, Beliefs, and Philosophy | Values, Goals & Motivations; Worldview, Beliefs & Attitudes | 我们把 values/goals 和 beliefs/attitudes 分开。 |
| Emotional and Relational Skills | Personality Traits; Cognitive & Capability Profile; Social Identity, Relationships & Community | 应该作为显式 subcategory 加入。 |
| Media Consumption and Engagement | Behavioral Patterns & Preferences; Domain-Specific Overlays | 对 social simulation 和 recommender systems 很重要。 |

## Attribute 构建计划

### Step 1：Aggregate Candidate Pool

从以下 sources 收集 candidate attributes：

- Yuexing 的 1K attributes；
- SCOPE；
- DeepPersona；
- Nemotron；
- PersonaHub；
- OASIS；
- PrimeX；
- WVS / GSS / ESS / Pew；
- Big Five / HEXACO / Facet MAP / IPIP；
- domain-specific benchmarks。

输出：

- 一个大型 candidate attribute pool；
- source metadata；
- 初始 category assignment。

### Step 2：Normalize

对每个 attribute 进行标准化：

- name；
- definition；
- category and subcategory；
- data type；
- allowed values or scale；
- aliases；
- source；
- theoretical basis；
- license notes；
- application relevance。

### Step 3：Deduplicate and Categorize

合并近似重复项，并保留 aliases。

示例：

- `political_leaning`、`political_orientation`、`political_affiliation` 应该检查定义后再决定合并或拆分。
- `risk_aversion`、`risk_tolerance`、`sensation_seeking` 应该建立关系，但不应自动合并。
- `openness`、`curiosity`、`intellectual_curiosity`、`need_for_cognition` 应该在 graph 中连接，但不能在未检查理论含义的情况下直接折叠成一个 attribute。

### Step 4：Grounding and Evidence

每个保留下来的 attribute 至少应该有一个 grounding source：

- validated psychological instrument；
- large-scale social survey；
- persona dataset；
- benchmark；
- domain literature；
- official population source。

Evidence level 可以标记为：

- High：validated psychological scale 或 official survey variable；
- Medium：peer-reviewed dataset / benchmark 中使用过；
- Low：LLM-mined 或 generated attribute，仍需要进一步 validation。

### Step 5：Attribute Graph

构建一个 graph，并包含以下 relation types：

- `synonym_of`；
- `parent_of`；
- `subtype_of`；
- `correlates_with`；
- `negatively_correlates_with`；
- `conflicts_with`；
- `depends_on`；
- `domain_specific_to`；
- `grounded_by`。

这个 graph 将帮助我们进行 deduplication、conflict detection 和 domain-specific persona assembly。

## 推荐输出结构

最终的 persona attribute system 应该有三层：

### Core Persona Schema

一组较小的、跨领域高价值 attributes。

目的：

- 作为稳定的 base persona；
- 易于检查；
- 对大多数 simulations 有用。

### Extended Attribute Pool

大型 optional attribute library，包括细粒度 personality facets、beliefs、preferences、routines 和 social context。

目的：

- 支持更丰富的 personas；
- 支持 long-tail diversity；
- 支持 source-grounded expansion。

### Domain Modules

面向具体任务的 attribute bundles。

示例：

- finance：risk tolerance、financial literacy、time horizon、debt stress、trust in institutions；
- education：prior knowledge、learning style、self-efficacy、motivation、academic anxiety；
- health：health status、health literacy、care access、medication adherence、risk perception；
- recommender：taste profile、media consumption、novelty seeking、budget、brand sensitivity；
- political / social survey：ideology、institutional trust、religiosity、civic participation、social issue attitudes。

## 实用规则

Top-level schema 应该由理论驱动。

Subcategories 应该由覆盖度驱动。

Individual attributes 应该有 evidence grounding。

DeepPersona 帮助我们补 coverage。SCOPE 帮助我们理解 LLM-persona structure。Big Five、HEXACO、Facet MAP、Schwartz、WVS、GSS、PrimeX、Census、IPUMS 帮助我们做 grounding。

## 简短总结

我们的 persona schema 基于：

- McAdams：提供整体 personality architecture；
- Big Five / HEXACO / Facet MAP / IPIP：支撑 personality traits；
- Schwartz / WVS / GSS / PrimeX：支撑 values、beliefs、worldview 和 attitudes；
- Social Identity Theory / Census / IPUMS / Nemotron：支撑 demographics 和 social context；
- Person-situation interaction / SCOPE：支撑 simulation logic。

DeepPersona 应该作为丰富的 subcategories 和 candidate attributes 来源使用，但不应作为最终 theoretical taxonomy。
