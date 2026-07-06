# Web interaction modes

PersonaBench supports **four Docker / no-use.computer** ways to run persona web
scenarios against **live public URLs**, plus **CUA** in Docker via
`persona-computer-1`. Pick the mode that fits the study — none is the global
default.

## Quick pick

| Mode | Task example | Agent | Environment | When to use |
|------|----------------|-------|-------------|-------------|
| **Playwright** | `application/tasks/example-web-playwright_quote-choice/` | `persona-openhands-sdk` | `docker` + `network_mode = "public"` | Terminal + Python Playwright; CI-friendly, lower cost |
| **browser-use** | `application/tasks/example-web-browser-use_laptop-choice/` | `persona-browser-use` | `docker` + `network_mode = "public"` | Dedicated browser agent loop; persona via `extend_system_message` |
| **Cocoa** | `application/tasks/example-web-cocoa_plan-choice/` | `persona-cocoa` | `docker` + AIO Sandbox image + `network_mode = "public"` | Unified browser + shell + files in one container |
| **CUA** | `application/tasks/example-web-cua_bookshop-choice/` | `persona-computer-1` | `docker` (Linux Xvfb) | Screenshot loop in Linux desktop; finish with **done** action |

Checked-in smoke recipes: [`configs/jobs/example-job-recipe/`](../configs/jobs/example-job-recipe/)
(`appSim-example-web-playwright-local.yaml`, `…-browser-use-local.yaml`, etc.).

## Shared submission contract

Live-web browse-and-choose tasks in this repo share a **persona decision**
JSON shape. Each task names its output file under `/app/output/`:

| Task | Output file | Live URL |
|------|-------------|----------|
| Playwright quote | `quote_choice.json` | https://quotes.toscrape.com/ |
| browser-use laptop | `laptop_choice.json` | https://webscraper.io/test-sites/e-commerce/static/computers/laptops |
| Cocoa plan | `plan_choice.json` | https://www.pythonanywhere.com/pricing/ |
| CUA bookshop | `book_interest.json` | https://books.toscrape.com/ |

Example shape (fields vary slightly per task — follow each task's `instruction.md`):

```json
{
  "decision_subject_id": "<stable slug or site id>",
  "decision_subject_label": "<title exactly as shown on the site>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "reason": "<why this matched you as this persona>"
}
```

Verifiers check **schema** and task-specific required fields, not semantic match
to the live catalog (pages change).

On **use.computer macOS** (computer-use tasks only), Harbor remaps `/app` →
`/Users/lume` in shell commands. Verifiers resolve this automatically;
**instructions always say `/app/output/`**.

Full metric contract: [task-spec/web/README.md](task-spec/web/README.md).

## Playwright mode

**How it works:** Chromium is controlled through the **Playwright API** (DOM
selectors). The agent (via OpenHands terminal) runs Python that calls
`page.goto()`, `locator()`, etc.

**Pros:** Faster, cheaper, more repeatable than CUA; JavaScript-rendered pages work.

**Cons:** Not a literal “human looking at the screen”; anti-bot / complex UX may
need extra handling.

**API key:** `persona-openhands-sdk` requires **`LLM_API_KEY`** on the host (not
`ANTHROPIC_API_KEY`). If you only have Anthropic set up:

```bash
export LLM_API_KEY="${ANTHROPIC_API_KEY}"
```

```bash
uv run harbor run \
  -a persona-openhands-sdk \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/example-web-playwright_quote-choice
```

Or the checked-in smoke recipe:

```bash
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-web-playwright-local.yaml
```

Oracle (no LLM):

```bash
uv run harbor run -p application/tasks/example-web-playwright_quote-choice -a oracle
```

**task.toml:** set `[environment].network_mode = "public"` and
`[agent].network_mode = "public"`. Runtime:
`environment/task-environments/application/shared-web-playwright/`.

## browser-use mode

**How it works:** The [browser-use](https://github.com/browser-use/browser-use)
library runs an agent loop over Chromium (DOM tools + optional vision). Persona
maps to **`extend_system_message`**; the task instruction stays in the `task` field.

**Pros:** Purpose-built web agent; MIT license; no `use-computer` cost.

**Cons:** Slower than hand-written Playwright; less flexible than full terminal access.

**API key:** `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `LLM_API_KEY` (mapped by
model provider).

```bash
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-web-browser-use-local.yaml
```

Oracle:

```bash
uv run harbor run -p application/tasks/example-web-browser-use_laptop-choice -a oracle
```

Runtime: `environment/task-environments/application/shared-web-browser-use/`.

## Cocoa mode (AIO Sandbox)

**How it works:** The task Docker image is
[`agent-infra/sandbox`](https://github.com/agent-infra/sandbox) (browser + shell
+ files on `localhost:8080`). [CocoaAgent](https://github.com/cocoabench/cocoa-agent)
connects in-process with `skip_docker`. Persona is merged into the **instruction**
(same slot as OpenHands / computer-1).

**Pros:** All-in-one digital agent without `use-computer`; no Docker socket mount.

**Cons:** Heavier base image than Playwright-only tasks.

```bash
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-web-cocoa-local.yaml
```

Runtime: `environment/task-environments/application/shared-web-cocoa/`.

## CUA mode (Chromium + computer-use)

**How it works:** A real desktop browser window in Docker (Xvfb + XFCE); each turn
the model receives a **screenshot** and returns actions (`navigate`, `click`,
`scroll`, …). The agent finishes with a **done** JSON action; Harbor materializes
`/app/output/book_interest.json`.

**Pros:** Closest to end-user behavior among Docker web modes; no
`USE_COMPUTER_API_KEY` for **Docker Linux** web CUA.

**Cons:** Slower and costlier than Playwright/browser-use; first run builds a
desktop image.

```bash
uv sync --extra computer-1
export ANTHROPIC_API_KEY=...
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-web-linux-cua-local.yaml
```

Oracle:

```bash
uv run harbor run -p application/tasks/example-web-cua_bookshop-choice -a oracle
```

Runtime: `environment/task-environments/application/shared-web-cua-linux/`.

For **macOS / iOS** screenshot CUA (system settings, not live web), use
`application/tasks/example-computer-use-*` with `-e use-computer` — see
[choosing-an-agent.md](choosing-an-agent.md).

## What we do *not* treat as a web mode

| Approach | Status |
|----------|--------|
| [Skyvern](https://github.com/Skyvern-AI/skyvern) | No `persona-skyvern` in this repo; use browser-use or CUA for vision-first browsing. |
| `curl` / `wget` only | Not a web interaction mode — no JS, no layout. OK for smoke, not persona web browsing. |
| Mock HTML sidecar | Deprecated for web examples here; use live URL tasks under `application/tasks/example-web-*`. |

## Authoring a new live-web application

1. Choose a mode from the table above.
2. Copy the closest `example-web-*` task; reuse the decision JSON contract or
   document a new schema inline in `instruction.md` and the task README.
3. Set `network_mode = "public"` where the agent must reach the internet.
4. Point `[environment].definition` at the matching `shared-web-*` runtime (or
   create a task-specific environment only when the stack is genuinely new).
5. Register the task for Cockpit — [task-guide.md § Cockpit registration](task-guide.md#cockpit-registration).
6. Add **Suggested setup (non-binding)** in `tasks/.../README.md` — do not put
   agent names in `instruction.md`.
7. Document URL stability and login requirements in README **Known limitations**.

## Reference tasks

| Task | Mode |
|------|------|
| `application/tasks/example-web-playwright_quote-choice/` | Playwright + live URL |
| `application/tasks/example-web-browser-use_laptop-choice/` | browser-use + live URL |
| `application/tasks/example-web-cocoa_plan-choice/` | Cocoa + live URL |
| `application/tasks/example-web-cua_bookshop-choice/` | CUA + live URL (Docker Linux) |

See also [task-guide.md](task-guide.md) and [choosing-an-agent.md](choosing-an-agent.md).

Play tasks in the PersonaEval Cockpit: [QUICKSTART.md §10](QUICKSTART.md#10-personaeval-cockpit--play-tasks-visually).
