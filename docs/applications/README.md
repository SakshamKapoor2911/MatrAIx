# Application team documentation

> Part of [MatrAIx](../../README.md). The Application team owns **MatrAIx simulation scenarios**.

## Paths in this repository

| Kind | Path |
|------|------|
| Executable tasks | `tasks/{survey,chat,web,computer-use}/` |
| Team docs | `docs/applications/` (this directory) |
| Detailed team plan | [PLAN.md](./PLAN.md) |
| Hello-world examples | `examples/tasks/` |
| Verifiers | `packages/rewardkit/` + per-task `tests/` |
| Scaffolding | `harbor task init`, `skills/create-task` |

**Convention:** Harbor task format; `instruction.md` = scenario; persona lives in the agent layer (`-a persona-*` + `persona_path`).

---

## Goal

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

## Example application areas

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

## Application template

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

## To write (Harbor implementation)

- [x] [`task-guide.md`](./task-guide.md) — instruction / environment / separate verifier / rewardkit
- [x] [`web-interaction.md`](./web-interaction.md) — Playwright vs CUA for live-web tasks
- [x] Reference scenarios under `tasks/` — see [tasks/README.md](../../tasks/README.md)
- [ ] Adapter output → root `tasks/` normalization checklist

## Contributing

- new task scenarios under `tasks/`
- domain-specific benchmarks
- evaluation metrics (`packages/rewardkit/`)
- analysis templates (`reporting/`)

See [contributing.md](../contributing.md).
