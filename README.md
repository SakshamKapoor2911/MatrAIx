# MatrAIx

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Discord](https://img.shields.io/badge/Discord-join-5865F2?logo=discord&logoColor=white)](https://discord.gg/vruP88PTZ)

> **Simulate before reality.**  
> Large-scale, persona-driven agent simulation — test products, conversations, and workflows *before* they hit real users.

MatrAIx pairs **synthetic personas** with **LLM agents** in reproducible Harbor tasks: surveys, chat, live web, and desktop computer-use. The name nods to *The Matrix* — a simulated world useful for exploration, not a replacement for real people.

**North star:** toward **8.3B** persona-scale simulation (one synthetic profile per person on Earth). Today the repo ships a working minimal stack you can run locally with Docker.

---

## 🚀 Quick start

**Prerequisites:** [uv](https://docs.astral.sh/uv/), Docker (for most tasks). Persona runs need API keys in your **shell environment** — see [`.env.example`](.env.example) for variable names ([choosing-an-agent.md](docs/environments/choosing-an-agent.md)).

```bash
git clone https://github.com/matraix-ai/matraix.git && cd matraix
uv sync

# Persona run — set ANTHROPIC_API_KEY in your shell (or ~/.zshrc) if not already
# First run builds the task Docker image; may take a few minutes.
uv run harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-20250514 \
  --ak persona_path=personas/examples/persona_0042.yaml \
  -p tasks/survey/product-feedback
```

Inspect results:

```bash
uv run harbor view jobs --build
```

> Use **`uv run harbor`** — a globally installed `harbor` may be an older build without `persona-*` agents.

---

## 🏗️ Architecture

| Team | Layer | Docs | Repo |
|------|-------|------|------|
| 🧬 **Persona** | *who* is simulated | [docs/personas/](docs/personas/README.md) | `personas/` |
| 🌐 **Environment** | *where* and *how* they act | [docs/environments/](docs/environments/README.md) | `configs/jobs/`, `src/harbor/`, `src/matraix/` |
| 📋 **Application** | *what* we simulate | [docs/applications/](docs/applications/README.md) | `tasks/` |

```mermaid
flowchart LR
    P["🧬 Persona<br/>synthetic population"] --> E["🌐 Environment<br/>execution & evaluation"]
    A["📝 Application<br/>tasks & scenarios"] --> E
    E --> R["📊 Traces, metrics,<br/>reports, benchmarks"]
```

A typical simulation pipeline: select or generate personas → instantiate agents → choose an environment → define tasks and evaluation → run → collect traces → analyze → generate reports or benchmark results.

---

## 💬 Join the project

We are actively looking for collaborators across Persona, Environment, and Application — research, engineering, data, and evaluation.

### 1. Join Discord

[![Discord](https://img.shields.io/badge/Discord-join%20MatrAIx-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/vruP88PTZ)

Chat with the team, ask questions, and find collaborators.

### 2. Fill out the interest form

[![Google Form](https://img.shields.io/badge/Google%20Form-join%20MatrAIx-4285F4?style=for-the-badge&logo=googleforms&logoColor=white)](https://forms.gle/hwEHng5HGWRqcJue9)

Share your background and interests. We read every submission and will get back to you as soon as possible.

---

## 📁 Repository layout

```text
├── src/matraix/          # Persona agents & MatrAIx extensions
├── src/harbor/           # Execution runtime (CLI, environments, viewer API)
├── personas/             # Persona YAML (+ Jinja templates)
├── tasks/                # Application task simulation
├── examples/tasks/       # Harbor hello-world examples
├── configs/jobs/         # Job YAML templates
├── packages/rewardkit/   # Verifier / LLM-judge toolkit
├── apps/viewer/          # Web UI for harbor view
└── docs/                 # Team documentation
```

---

## 🗺️ Roadmap

- **Stage 1 — Minimal stack.** Persona schema, initial persona set, basic survey + chatbot environments, first persona-adherence benchmark, simple telemetry.
- **Stage 2 — Core dataset & benchmark.** Release MatrAIxPersona-8B, MatrAIxPersonaTrain, MatrAIxPersonaBench; add domain subsets and automatic evaluation.
- **Stage 3 — Environment expansion.** Web environment, long-horizon and multi-turn tasks, memory-enabled agents, multi-agent interaction, cost/friction simulation.
- **Stage 4 — Simulated society.** Scale toward a planet-scale population with social graphs, group interaction, information diffusion, and synthetic communities.

---

## 🔬 Research questions

- How should synthetic personas be represented, and how do we measure persona adherence?
- How consistent are LLM agents across long interactions?
- Can simulated users predict real user preferences?
- How do multi-agent simulations differ from single-agent feedback?
- Can lightweight self-evolving memory make agents better human stand-ins?
- What are the limitations and failure modes of persona-based simulation?

---

## 📄 Publications

MatrAIx is intended to produce two initial papers, with more to follow as the project grows.

- **Paper 1 — Persona data & benchmark.** Construction of the large-scale MatrAIxPersona dataset and the MatrAIxPersonaBench persona-adherence benchmark, covering schema design, data generation, quality filtering, and evaluation.
- **Paper 2 — User simulation.** Downstream applications of persona-conditioned agents as simulated users, with task scenarios, evaluation, and analysis of how well simulated feedback stands in for real users.

**Timeline.** Both papers target completion over the summer of 2026.

As the project grows, we expect **additional papers** — for example, more advanced persona-agent methods, evaluation methodology, and broader, more comprehensive simulation applications.

---

## 🤝 Contributing

We welcome contributions in all three areas:

- [Contributing guide](docs/contributing.md)
- [Persona team](docs/personas/README.md) · [Environment](docs/environments/README.md) · [Application](docs/applications/README.md)

---

## ⚠️ Limitations

MatrAIx is **experimental**. Synthetic users are not real users — use outputs for exploration, hypothesis generation, and early signal only. Validate important decisions with real-world data. Agents can be inconsistent, biased, or prompt-sensitive.

---

<p align="center"><strong>Simulate before reality.</strong></p>
