# MatrAIx

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Discord](https://img.shields.io/badge/Discord-join-5865F2?logo=discord&logoColor=white)](https://discord.gg/vruP88PTZ)

> **Simulate before reality.**  
> Large-scale, persona-driven agent simulation — test products, conversations, and workflows *before* they hit real users.

MatrAIx pairs **synthetic personas** with **LLM agents** in reproducible Harbor tasks: surveys, chat, live web, and desktop computer-use. The name nods to *The Matrix* — a simulated world useful for exploration, not a replacement for real people.

**North star:** toward **8.3B** persona-scale simulation (one synthetic profile per person on Earth). Today the repo ships a working minimal stack you can run locally with Docker.

---

## 🏗️ Architecture

![MatrAIx architecture](docs/assets/matraix-architecture.png)

| Team | Delivers | Docs |
|------|----------|------|
| 🧬 **Persona** | Persona cards, datasets, adherence benchmarks | [docs/personas/](docs/personas/README.md) |
| 🌐 **Environment** | Harbor runtime, agents, jobs, viewer | [docs/environments/](docs/environments/README.md) |
| 📋 **Application** | Simulation scenarios (survey, chat, web, computer-use) | [docs/applications/](docs/applications/README.md) |

**Agents & API keys (Application + Environment):** [choosing-an-agent.md](docs/environments/choosing-an-agent.md)

---

## 🚀 Quick start

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/) and [uv](https://docs.astral.sh/uv/). An API key is only needed for the examples below — see [`.env.example`](.env.example) and [choosing-an-agent.md](docs/environments/choosing-an-agent.md).

```bash
git clone https://github.com/matraix-ai/matraix.git && cd matraix
uv sync
```

**Smoke** (no API key) — Harbor `hello-world` task; checks Docker and the runtime (first run builds the image; may take a few minutes):

```bash
uv run harbor run -c configs/jobs/example-job-recipe/harbor-smoke-local.yaml
```

**Example (Application)** — one persona, open-text product survey (product metrics, no grounding oracle):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # if not already in your shell

uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-survey-local.yaml
```

**Example (Persona)** — same persona, **bench** survey (MCQ grounding check on `economic_motivation`):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # if not already in your shell

uv run harbor run -c configs/jobs/example-job-recipe/personaBench-example-survey-local.yaml
```

**View** — inspect runs (`jobs/` includes examples you can browse without re-running):

```bash
uv run harbor view jobs --build
```

> Use **`uv run harbor`** — a globally installed `harbor` may be an older build without `persona-*` agents.

Step-by-step guides: [Application getting started](docs/applications/getting-started.md) · [Persona getting started](docs/personas/getting-started.md)

---

## 💬 Join the project

We welcome collaborators across research, product, data, and engineering.

### 1. Say hello

[![Discord](https://img.shields.io/badge/Discord-join%20MatrAIx-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/vruP88PTZ)

[![Google Form](https://img.shields.io/badge/Google%20Form-join%20MatrAIx-4285F4?style=for-the-badge&logo=googleforms&logoColor=white)](https://forms.gle/hwEHng5HGWRqcJue9)

### 2. Read docs and pick a team (or teams)

| Team | If you care about… | Start here |
|------|-------------------|------------|
| 🧬 **Persona** | Persona schema and data, persona generator, persona grounding | [docs/personas/](docs/personas/README.md)<br>[getting started](docs/personas/getting-started.md) |
| 📋 **Application** | Product scenarios, task design, product user metrics design | [docs/applications/](docs/applications/README.md)<br>[getting started](docs/applications/getting-started.md) |
| 🌐 **Environment** | Environment infra, engineering, runtime, back and front end | [docs/environments/](docs/environments/README.md) |

All teams that run simulations should skim [choosing-an-agent.md](docs/environments/choosing-an-agent.md).

### 3. Do one hands-on pass

Complete your team’s getting-started guide (or the smoke run above), then browse results with `harbor view`.

### 4. Contribute

Discuss on **Discord** or open a **GitHub issue** before a large PR — [contributing guide](docs/contributing.md).

---

## 📁 Repository layout

```text
# —— All teams ——
docs/                    # Team documentation (personas/, environments/, applications/)
jobs/                    # Run outputs (example runs checked in for harbor view)

# —— Persona team ——
persona/
├── dimensions.json
├── datasets/            # Persona YAML pools (bench-dev-2000, …)
├── tasks/               # Persona-adherence Harbor tasks
├── scripts/
└── reporting/

# —— Application team ——
application/
├── tasks/               # Executable scenarios (survey, chat, web, computer-use)
├── scripts/
└── reporting/

# —— Environment team ——
src/harbor/              # CLI, trial/job runtime, Docker/Modal/Daytona/… backends
src/matraix/             # Persona agents (persona-claude-code, …)
configs/jobs/            # Job YAML recipes (smoke, persona bench, application)
packages/rewardkit/      # Verifier / LLM-judge toolkit
apps/viewer/             # Web UI for harbor view
examples/tasks/          # Upstream Harbor hello-world (reference)
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

- **Paper 1 — Survey.** A survey of agent personas and user simulation: how synthetic personas and persona-conditioned agents are built, evaluated, and used to simulate users, covering existing datasets, methods, benchmarks, and open challenges.
- **Paper 2 — MatrAIx persona & user simulation.** Our own end-to-end work, presenting the MatrAIxPersona dataset and MatrAIxPersonaBench together with persona-conditioned agents used as simulated users — schema design, data generation, quality filtering, evaluation, and downstream simulation applications in a single paper.

**Timeline.** Both papers target completion over the summer of 2026.

---

## 🤝 Contributing

- [Contributing guide](docs/contributing.md)
- [Persona team](docs/personas/README.md) · [Environment](docs/environments/README.md) · [Application](docs/applications/README.md)

---

## ⚠️ Limitations

MatrAIx is **experimental**. Synthetic users are not real users — use outputs for exploration, hypothesis generation, and early signal only. Validate important decisions with real-world data. Agents can be inconsistent, biased, or prompt-sensitive.

---

<p align="center"><strong>Simulate before reality.</strong></p>
