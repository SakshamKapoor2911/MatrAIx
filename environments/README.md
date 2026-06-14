# 🌐 Team 2: Environment

> Part of [MatrAIx](../README.md). The Environment team builds the simulation environments where persona-affiliated agents interact with tasks, systems, products, interfaces, and other agents.

This team is responsible for the execution layer of MatrAIx.

## 🎯 Goal

The goal is to create reusable environments that allow agents to perform realistic tasks under controlled conditions.

An environment defines:

- what the agent can observe
- what actions the agent can take
- what tools or interfaces are available
- what the task objective is
- how the interaction is logged
- how the outcome is evaluated

## 🧱 Environment Types

We organize environments along a spectrum of increasing interaction complexity. The earlier types are simpler to build and deploy, while the later types require more engineering and are longer-term efforts. Early development should prioritize the simpler surfaces.

### 📝 Type 1: Survey Environment

The simplest environment. Agents read a prompt, product concept, message, description, policy, UI mockup, or decision scenario, then provide structured feedback. At this level, an agent behaves much like an LLM answering a questionnaire rather than a tool-using agent.

Useful for: product concept testing, messaging evaluation, survey simulation, preference elicitation, synthetic focus groups, and early-stage idea validation.

Example task:

```text
Read this product description and answer:
1. Would you use this product?
2. What confuses you?
3. What do you like?
4. What would make you stop using it?
5. How likely are you to recommend it?
```

Possible outputs: rating scores, free-form feedback, ranked preferences, objections and confusion points, and predicted adoption likelihood.

### 💬 Type 2: Chatbot Environment

Designed for evaluating AI assistants, chatbots, LLM products, AI companions, customer support agents, AI tutors, AI SDRs, and other conversation-based systems.

Persona agents interact with a target chatbot and evaluate the experience. This environment is especially natural because many modern products *are themselves* AI systems, so they can be tested directly through conversation without any UI automation.

Example domains: AI customer support, AI sales agents, AI tutors, AI companions, coding assistants, healthcare chatbots, financial advisors, and internal enterprise copilots.

Example task:

```text
You are a first-time user trying to understand whether this AI assistant
can help you choose a health insurance plan. Ask questions naturally,
express confusion when appropriate, and evaluate whether the assistant
is trustworthy.
```

Metrics may include: helpfulness, trustworthiness, clarity, safety, persuasion, user satisfaction, conversation length, unresolved questions, escalation likelihood, and persona-specific response quality.

### 🌐 Type 3: Web Environment

Supports agent interaction with web-based products, websites, dashboards, landing pages, and web applications.

Early versions may focus on lightweight web surfaces rather than full production systems. There are two natural integration paths: MatrAIx hosts a sandbox playground where a contributor or user supplies the web surface, or MatrAIx exposes an agent API that an external system drives against its own web product.

Possible input formats: public URL, static HTML, hosted prototype, landing page, Figma-to-code prototype, documentation page, or sandbox web app.

Useful for: onboarding flow evaluation, landing page testing, checkout flow analysis, feature discoverability, web UX friction detection, and documentation usability testing.

Example task:

```text
You are a small business owner evaluating this SaaS landing page.
Try to understand what the product does, whether pricing is clear,
and whether you would sign up for a demo.
```

Possible logged signals: pages visited, clicks, scroll behavior, hesitation points, failed actions, confusion moments, the final decision, and natural-language feedback.

### 📱 Type 4: App / Sandbox Environment

Intended for more complex interactive products, including mobile apps, desktop apps, and sandboxed prototypes.

This is a longer-term environment type because full app simulation introduces many engineering challenges, such as authentication, UI automation, device state, build compatibility, and environment reset. As with the web environment, integration can happen either through a hosted sandbox playground or through an agent API.

Possible input formats:

- Android `.apk` / `.aab` (debug or sandbox build)
- iOS simulator build, `.ipa`, or TestFlight build
- desktop signed installer or sandbox build (`.dmg`, `.exe`, `.app`)
- controlled prototype build
- local sandbox environment

Useful for: mobile onboarding flows, app navigation testing, feature discovery, workflow completion, long-horizon task evaluation, and multi-session behavior simulation.

For early-stage development, MatrAIx prioritizes simpler surfaces (surveys, chatbots, and lightweight web prototypes) before expanding into full app automation, which tends to pull in low-value engineering work such as account state, login, captchas, and environment cleanup.

## 🔮 Future Environment Directions

### Long-Horizon Task Environments

Many realistic tasks do not produce immediate feedback. A user may need to interact with a system over multiple sessions before forming an opinion or changing behavior (e.g. learning with an AI tutor over several days, or evaluating a finance app after multiple portfolio updates).

These environments require persistent memory, planning, longitudinal state, multi-step workflows, temporal evaluation, and optionally lightweight self-evolving agents that update their behavior across sessions to better mimic how humans learn and adapt.

### Multi-Agent Social Environments

Many real-world systems involve groups of people rather than isolated users: social networks, group chats, online communities, recommendation ecosystems, multiplayer games, marketplaces, and workplace collaboration.

This direction lets us study not only individual user behavior, but also network effects, social influence, coordination, competition, and emergent group dynamics.

### Cost and Friction Simulation

In addition to quality-based feedback (whether users like something), MatrAIx can also simulate user-side and system-side cost: number of steps required, time-to-completion, cognitive load, clarification turns, token cost, dropout probability, and implementation cost of different workflows.

This allows environments to evaluate not only whether a product is preferred, but also how expensive, slow, or difficult it is to use.

## 🤝 Contributing

- survey environments
- chatbot environments
- web interaction environments
- sandbox environments
- logging and telemetry tools
- evaluation protocols
