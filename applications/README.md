# 🧪 Team 3: Application

> Part of [MatrAIx](../README.md). The Application team builds task libraries, evaluation scenarios, and domain-specific simulation recipes on top of the Persona and Environment layers.

This team focuses on a single question:

> What should we simulate, and how do we evaluate whether the simulation is useful?

## 🎯 Goal

The Application team collects realistic scenarios where persona-affiliated agents can be used for evaluation, analysis, research, or experimentation, and makes sure each scenario can actually run end-to-end inside a Team 2 environment.

Each application should define:

- task type (Survey / Chatbot / Web / App)
- domain / vertical
- product under test
- task specification
- environment needs
- persona (simulated user)
- user goal & context
- metrics
- outputs

## 📚 Example Application Areas

A non-exhaustive set of domains where persona agents can drive evaluation. Each becomes a concrete scenario using the [Application Template](#-application-template) below.

| # | Area | Example questions |
|---|------|-------------------|
| 1 | **Product Concept Testing** | Would this persona understand and care about the product? Which positioning is most compelling? |
| 2 | **Onboarding & UX** | Where do users get confused? Which step creates the most friction? |
| 3 | **Conversational AI** | Is the assistant clear and trustworthy? Does it adapt to the user's background? |
| 4 | **AI Red-Teaming** | Can the system handle frustrated, confused, or adversarial users without unsafe behavior? |
| 5 | **Market & User Research** | How do segments react? What objections and unmet needs surface? |
| 6 | **Education & Tutoring** | Are tutor explanations clear? How do different learning styles engage? |
| 7 | **E-Commerce & Recsys** | Where does checkout break down? Which promotions and recommendations work? |
| 8 | **Gaming** | How do mechanics affect retention, progression, and player frustration? |
| 9 | **Enterprise SaaS** | Are features discoverable? Where do workflows stall? |
| 10 | **Synthetic Data Generation** | Generate conversations, preference data, journey traces, and interaction logs. |

## 📝 Application Template

Each application scenario should be described in a consistent format so it can be reproduced and handed to the Environment team to run:

```text
Scenario name:
Task type:                # 1·Survey / 2·Chatbot / 3·Web / 4·App   (the four types in PLAN.md)
Domain / vertical:        # first focus set: Software · Finance · Healthcare · Commerce & Retail
Product under test:       # WHAT we're evaluating, named concretely
Task specification:       # the concrete task: what happens in the episode + what the agent/user must do
Environment needs:        # what the Environment team must set up: surface + how to connect + initial state/data/tools
Persona (simulated user): # which persona traits/dimensions matter (e.g. price-sensitivity, age, shopping habits)
User goal & context:      # the persona's specific motivation + what they already know
Metrics:                  # signals to collect (clarity, satisfaction, friction, task completion…)
Outputs:                  # telemetry / trajectory the env emits → feeds the report
```

Example:

```markdown
Scenario name: Retail order-support refund handling
Task type: 2·Chatbot
Domain / vertical: Commerce & Retail / order support
Product under test: a retail order-support chatbot (chat API)
Task specification: Simulated shoppers request a return/refund over multi-turn chat; the bot must
                    handle each per the return policy (≤30 turns each).
Environment needs: connect to the bot's chat API; load an orders DB (order #4521) + the return policy
Persona: price-sensitivity, age, shopping habits, tech-savviness
User goal & context: "You ordered NovaBuds earbuds; they arrived late; you want a full refund"
Metrics: persona adherence, frustration, turns-to-resolution, policy-followed (yes/no)
Outputs: conversation trajectory + per-metric scores
```

## 🤝 Contributing

- new task scenarios
- domain-specific benchmarks
- example simulations
- evaluation metrics
- analysis templates
- synthetic data generation recipes
