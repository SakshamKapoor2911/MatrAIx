# MatrAIx task authoring guide

How to build MatrAIx simulation tasks on Harbor.

## Layout

```
tasks/<form>/<scenario>/
├── task.toml           # timeouts, resources, metadata
├── instruction.md      # scenario (what to do) — NOT persona traits
├── environment/        # agent container (Dockerfile or compose)
├── tests/              # verifier (test.sh + helpers)
├── solution/           # optional oracle (solve.sh)
└── README.md           # suggested agent, example run
```

**Forms:** `survey`, `chat`, `web`, `computer-use` (see [tasks/README.md](../../tasks/README.md)).

## Persona vs task

| Layer | Where | Content |
|-------|-------|---------|
| **Who** | `personas/examples/*.yaml` + `-a persona-*` | Demographics, psychology, communication style |
| **What** | `instruction.md` | Scenario, goals, output format |

Do not put task scenarios in persona YAML. v1 personas use structured domains only.

## instruction.md

- State the goal and required output paths/formats.
- **MatrAIx convention:** task inputs under `/app/input/`; agent submissions under `/app/output/` only.
- Describe success without leaking verifier logic.
- Keep tone neutral — the persona agent supplies voice and preferences.

## environment/

MatrAIx Docker task layout inside the container:

```
/app/
├── input/     # seeded task assets (COPY from environment/)
└── output/    # agent submissions only (collected to host)
```

- **Docker** (default): `environment/Dockerfile` — survey, chat, web tasks.
- **use-computer**: no Dockerfile; run with `-e use-computer` (see `tasks/computer-use/notification-preferences/`).
- Seed static assets (briefs, mock pages) via `COPY` into `/app/input/`.
- Pre-create `/app/input/` and `/app/output/` in the Dockerfile.

Test interactively:

```bash
harbor task start-env -p tasks/survey/product-feedback -e docker -a -i
```

## Verifier modes

| Mode | When | Config |
|------|------|--------|
| **Shared** (default) | Verifier runs in agent container; inspects `/app/output` artifacts | `tests/test.sh` + pytest |
| **Separate** | Hide verifier deps/keys from agent | `[verifier] environment_mode = "separate"` in `task.toml` |

Smoke tasks used **shared** pytest verifiers during early development. Production MatrAIx tasks should use **separate verifier + rewardkit** so grading is isolated from the agent.

## Reward Kit (production)

For multi-criteria or LLM-judged persona adherence:

```bash
# tests/test.sh
uvx --from harbor-rewardkit rewardkit /tests
```

See `skills/rewardkit` and `examples/tasks/reward-kit-example/`.

## Persona agents

| Form | Suggested agent |
|------|-----------------|
| survey, chat | `persona-claude-code` |
| web | `persona-openhands-sdk`, `persona-browser-use`, `persona-cocoa`, or `persona-computer-1` (CUA) |
| computer-use | `persona-computer-1` |

```bash
harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-20250514 \
  --ak persona_path=personas/examples/persona_0042.yaml \
  -p tasks/survey/product-feedback
```

Chat example: `tasks/chat/acme-support-mcp`.

Agent selection is **non-binding** in task READMEs — experimenters choose explicitly ([choosing-an-agent.md](../environments/choosing-an-agent.md)).

## Job configs

Batch local reference run:

```bash
uv run harbor run -c configs/jobs/persona-debug-local.yaml
```

Live web and computer-use have dedicated job YAMLs under `configs/jobs/` (see [web-interaction.md](./web-interaction.md)).

## Artifacts (submission files on the host)

Agent submissions live under `/app/output/`. Task inputs (briefs, mock pages) live in `/app/input/` and are not collected.

Each MatrAIx Docker task declares the output directory in `task.toml`:

```toml
artifacts = ["/app/output"]
```

After a run you should see e.g. `jobs/.../artifacts/app/output/survey_responses.json`. Alternatively, pass `--artifact /app/output` on the CLI or list paths under `artifacts:` in a job YAML (`examples/configs/artifacts-job.yaml`).

Harbor also auto-collects `/logs/artifacts/` (volume mount) if you use that convention instead.

### Chat with MCP (multi-turn)

For real conversational tasks, run a mock product chatbot as a **compose sidecar** and declare it in `task.toml`:

```toml
[[environment.mcp_servers]]
name = "acme-support"
transport = "streamable-http"
url = "http://support-bot:8000/mcp"
```

See `tasks/chat/acme-support-mcp/` and `examples/tasks/hello-mcp/`. Requires local **docker** (compose networking).

### Web (live public sites)

Contributors choose **Playwright** or **CUA** per application. Full guide: [web-interaction.md](./web-interaction.md).

| Mode | Task | Agent | Environment |
|------|------|-------|-------------|
| Playwright | `tasks/web/books-interest-playwright/` | `persona-openhands-sdk` | `docker`, `network_mode = "public"` |
| browser-use | `tasks/web/books-interest-browser-use/` | `persona-browser-use` | `docker`, `network_mode = "public"` |
| Cocoa | `tasks/web/books-interest-cocoa/` | `persona-cocoa` | `docker`, `network_mode = "public"` |
| CUA | `tasks/web/books-interest-cua/` | `persona-computer-1` | `-e use-computer` |

Playwright: set **`LLM_API_KEY`** on the host (`export LLM_API_KEY="$ANTHROPIC_API_KEY"`). See [choosing-an-agent.md](../environments/choosing-an-agent.md) and [web-interaction.md](./web-interaction.md).

### Computer-use (real desktop)

Desktop tasks use `-e use-computer` and **`persona-computer-1`**. Prefer **`/app/output/`** in instructions (MatrAIx convention). On use-computer **macOS**, Harbor maps `/app` → `/Users/lume` in shell commands; verifiers should resolve both.

- Reference: `tasks/computer-use/notification-preferences/`

## Oracle / CI

Verify task structure without an LLM:

```bash
harbor run -p tasks/survey/product-feedback -a oracle
```

## Adapter → tasks/

When importing external benchmarks via `adapters/`:

1. Normalize to Harbor task layout under `tasks/<form>/`.
2. Move scenario text to `instruction.md`; strip persona assumptions.
3. Add `README.md` with domain + suggested agent.
4. Keep upstream license notices in task README or `NOTICE` if required.

## Related

- [applications/README.md](./README.md)
- [skills/create-task](../../skills/create-task/SKILL.md)
- [personas/README.md](../../personas/README.md)
