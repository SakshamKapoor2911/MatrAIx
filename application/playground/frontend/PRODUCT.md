# PRODUCT.md — Playground Workbench

register: product

## What it is
A developer workbench to **test interactive apps (chatbots, surveys, websites) against simulated "persona" users** and score how well the app does — before real users do. Frontend is a React 18 + Vite + Tailwind 3 + TanStack Query SPA at `application/playground/frontend`, served by the Playground backend (dev at `:8765`).

## Who uses it
Researchers / engineers iterating on an application under test. They are in a focused task: configure a run, watch a simulated user drive the app, and read the scores. The tool should disappear into that task (product register — earned familiarity, not decoration).

## Surfaces & primary flows
- **Chat** — manual operator conversation: a human plays the user against the app (3-pane: session rail · conversation · turn inspector).
- **Playground** — the core: pick **Application type** (Chatbot / Survey / Web); for Chatbot pick an **application** (RecAI / OpenBB / Medical); choose a **persona** + run knobs; **Run eval** → watch the live trajectory + pipeline, then read the scorecard. Setup-form → live-run flow.
- **Runs** — history list, per-run debrief (option-aware), side-by-side compare.
- **Catalog** — browse/search 336 personas (sources: Nemotron / OASIS / PRIMEX / PersonaHub) + a persona detail drawer; reachable via ⌘K.

## Hard constraints
- **Pure frontend** when redesigning: keep the data layer (api.ts, hooks, query keys, types) and backend contract. Per-option fidelity matters (chatbot-only runtime panel; RecAI-only Domain; 3/3/4-node pipelines; distinct scoring).
- **Dark default + light** (persisted `<html>.light` toggle). **Friendly, tutorial-first copy** for first-time users; restrained/professional tone — no fake telemetry, no roleplay.

## Design system
MatrAIx / Playground — see [DESIGN.md](./DESIGN.md). The design system is implemented in the frontend tokens, Tailwind config, and shared cockpit components.
