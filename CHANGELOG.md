# Changelog

All notable changes to **MatrAIx** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Reference scenarios under `tasks/` (chat, web, computer-use) and job configs in `configs/jobs/`
- `docs/applications/task-guide.md` and `configs/jobs/example-job-recipe/appSim-example-debug-local.yaml`
- Tier 1 persona agents: `persona-claude-code`, `persona-computer-1`, `persona-openhands-sdk`
- Persona YAML loader (`matraix.agents.persona`) and `persona_meta.json` trial metadata
- Registered persona agents in Harbor `AgentName` + `AgentFactory`

### Changed

- `README.md`, `AGENTS.md`, and `CITATION.cff` rewritten for MatrAIx
- `pyproject.toml` workspace includes `matraix` package scaffold

### Removed

- Dev-only Phase 2 smoke tasks (superseded by reference scenarios under `tasks/`)
- Harbor Next.js documentation site from `docs/`
- `registry.json` and Harbor Hub / parity / docs-deploy automation assets
