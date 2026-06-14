# 🧪 Team 3: Application

> Part of [MatrAIx](../README.md). The Application team builds task libraries, evaluation scenarios, and domain-specific simulation recipes on top of the Persona and Environment layers.

This team focuses on a single question:

> What should we simulate, and how do we evaluate whether the simulation is useful?

## 🎯 Goal

The Application team collects realistic scenarios where persona-affiliated agents can be used for evaluation, analysis, research, or experimentation, and makes sure each scenario can actually run end-to-end inside a Team 2 environment.

Each application should define:

- target domain
- task setting
- relevant persona types
- required environment
- interaction protocol
- evaluation metrics
- expected output format
- example runs
- known limitations

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

Each application scenario should be described in a consistent format so it can be reproduced and shared:

```text
Scenario name:
Target domain:
Environment type:
Persona requirements:
Task prompt:
Interaction protocol:
Evaluation metrics:
Expected outputs:
Example run:
Known limitations:
```

Example:

```markdown
## Scenario: AI Tutor Evaluation for High School Algebra

Target domain: Education
Environment type: Chatbot Environment

Persona requirements:
Students with different math confidence levels, learning styles, and
attention spans.

Task prompt:
Interact with the AI tutor to learn how to solve a quadratic equation.
Ask questions naturally and express confusion when the explanation is unclear.

Evaluation metrics:
- clarity
- student confidence
- number of unresolved confusions
- correctness of final answer
- engagement
- persona-specific satisfaction

Expected outputs:
- conversation transcript
- student feedback
- tutor failure points
- improvement suggestions
```

## 🤝 Contributing

- new task scenarios
- domain-specific benchmarks
- example simulations
- evaluation metrics
- analysis templates
- synthetic data generation recipes
