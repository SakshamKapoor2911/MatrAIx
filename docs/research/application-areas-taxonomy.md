# Application Areas Taxonomy

This note is migrated from MatrAIx PR
[`#24`](https://github.com/MatrAIx-ai/MatrAIx/pull/24). It preserves the
application taxonomy without importing the old planning tree.

The taxonomy is non-exhaustive. It groups application scenarios by evaluation
objective rather than by industry vertical, so new survey, chat, web, and app
tasks can be added without changing the top-level structure.

| Application area | Application type | User-centric question |
|---|---|---|
| Product research | Product concept testing | How do different users understand, value, and respond to a new product concept? |
| Product research | Feature prioritization | Which features matter most to different user segments, and why? |
| Product research | Pricing and packaging | How do different users perceive pricing, value, and willingness to pay? |
| Market and user research | User segmentation | How do different user groups think, behave, and make decisions? |
| Market and user research | Pain point discovery | What frustrations, unmet needs, and motivations emerge across personas? |
| Marketing and advertising | Message testing | Which messages resonate with different user groups and why? |
| Marketing and advertising | Brand perception | How do different personas perceive and trust a brand? |
| UX and product evaluation | Onboarding evaluation | Which users struggle during onboarding, and where does friction occur? |
| UX and product evaluation | User journey analysis | How do different personas move through a workflow, and where do they abandon tasks? |
| UX and product evaluation | Accessibility evaluation | Which users face barriers when interacting with the product? |
| Conversational AI evaluation | Persona adaptation | How well does the AI adapt to users with different backgrounds, goals, and communication styles? |
| Conversational AI evaluation | Task completion | Which users successfully accomplish their goals, and which encounter difficulties? |
| Customer support and service | Issue resolution | How effectively can different users resolve problems and obtain support? |
| Customer support and service | Escalation handling | Which user types become frustrated, confused, or dissatisfied during support interactions? |
| Recommendation systems | Preference alignment | How well do recommendations align with the preferences of different users? |
| Recommendation systems | Trust and acceptance | Which users trust, accept, or reject recommendations, and why? |
| Recommendation systems | Diversity and exploration | How willing are different personas to explore unfamiliar recommendations? |
| Learning and knowledge transfer | Learning effectiveness | How effectively do different users learn from explanations, feedback, and guidance? |
| Learning and knowledge transfer | Knowledge assessment | How do learning outcomes vary across user groups and learning styles? |
| AI safety and trust evaluation | Privacy-sensitive users | How do privacy-conscious users respond to the system's handling of personal information? |
| AI safety and trust evaluation | Vulnerable users | How does the system influence users who may be easily misled, manipulated, or over-reliant on AI? |
| AI safety and trust evaluation | Trust calibration | Do different users develop appropriate levels of trust in the system's outputs? |
| Productivity and workflow assistance | Workflow optimization | Which users benefit most from workflow assistance, and where do bottlenecks remain? |
| Productivity and workflow assistance | Knowledge assistance | How effectively can different users find and apply relevant information? |
| Community and social interaction | Engagement analysis | What motivates different users to participate, contribute, and remain active in communities? |
| Community and social interaction | Moderation evaluation | How do different user groups perceive fairness, safety, and moderation decisions? |
| Gaming and interactive experiences | Retention analysis | Which player personas continue engaging over time, and which are likely to churn? |
| Gaming and interactive experiences | Progression and difficulty evaluation | How do different players respond to challenge levels, progression speed, and reward structures? |
| Gaming and interactive experiences | Reward and incentive design | Which rewards, achievements, and progression systems motivate different player types? |
| Gaming and interactive experiences | Social play and collaboration | How do different personas interact with teammates, communities, and multiplayer systems? |
| Gaming and interactive experiences | Player experience evaluation | How do different players perceive enjoyment, immersion, frustration, and satisfaction throughout gameplay? |
| Synthetic data generation | User journey simulation | Can realistic user behaviors, preferences, and interaction traces be generated across diverse personas? |

## Design Principles

- Persona-centric: each application area should meaningfully depend on user
  characteristics, preferences, goals, or behaviors.
- Cross-domain: areas are organized by evaluation objective rather than by a
  single industry.
- Scenario-driven: each application type can map to concrete survey, chat,
  web, or app scenarios.
- Extensible: new application tasks should fit without changing the top-level
  taxonomy unless a genuinely new evaluation objective appears.
