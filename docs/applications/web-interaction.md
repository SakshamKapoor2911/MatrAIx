# Web interaction modes (MatrAIx)

MatrAIx supports **four Docker / no-use.computer** ways to run persona web scenarios against **live public URLs**, plus **CUA** on `use-computer`. Pick the mode that fits the study — none is the global default.

## Quick pick

| Mode | Task example | Agent | Environment | When to use |
|------|----------------|-------|-------------|-------------|
| **Playwright** | `tasks/web/books-interest-playwright/` | `persona-openhands-sdk` | `docker` + `network_mode = "public"` | Terminal + Python Playwright; CI-friendly, lower cost |
| **browser-use** | `tasks/web/books-interest-browser-use/` | `persona-browser-use` | `docker` + `network_mode = "public"` | Dedicated browser agent loop; persona via `extend_system_message` |
| **Cocoa** | `tasks/web/books-interest-cocoa/` | `persona-cocoa` | `docker` + AIO Sandbox image + `network_mode = "public"` | Unified browser + shell + files in one container |
| **CUA** | `tasks/web/books-interest-cua/` | `persona-computer-1` | `use-computer` | Screenshot loop on remote desktop; highest human fidelity |

## Shared submission contract

Live-web tasks use the same JSON shape and **the same submission path**:

**`/app/output/book_interest.json`**

On **use-computer macOS**, Harbor remaps `/app` → `/Users/lume` in shell commands, so the file lands at `/Users/lume/output/book_interest.json`. Verifiers and oracle scripts resolve this automatically; **instructions always say `/app/output/`**.

```json
{
  "title": "<book title as shown on the site>",
  "price_gbp": "<price as shown, e.g. £51.77>",
  "interested": true,
  "reason": "<persona explanation>"
}
```

Verifiers check **schema only**, not semantic match to the live catalog (pages change).

## Playwright mode

**How it works:** Chromium is controlled through the **Playwright API** (DOM selectors). The agent (via OpenHands terminal) runs Python that calls `page.goto()`, `locator()`, etc.

**Pros:** Faster, cheaper, more repeatable than CUA; JavaScript-rendered pages work.

**Cons:** Not a literal “human looking at the screen”; anti-bot / complex UX may need extra handling.

**API key:** `persona-openhands-sdk` requires **`LLM_API_KEY`** on the host (not `ANTHROPIC_API_KEY`). If you only have Anthropic set up:

```bash
export LLM_API_KEY="${ANTHROPIC_API_KEY}"
```

```bash
uv run harbor run \
  -a persona-openhands-sdk \
  -m anthropic/claude-sonnet-4-20250514 \
  --ak persona_path=personas/examples/persona_0042.yaml \
  -p tasks/web/books-interest-playwright
```

Oracle (no LLM):

```bash
uv run harbor run -p tasks/web/books-interest-playwright -a oracle
```

**task.toml:** set `[environment].network_mode = "public"` and `[agent].network_mode = "public"`.

## browser-use mode

**How it works:** The [browser-use](https://github.com/browser-use/browser-use) library runs an agent loop over Chromium (DOM tools + optional vision). MatrAIx persona maps to **`extend_system_message`**; the task instruction stays in the `task` field.

**Pros:** Purpose-built web agent; MIT license; no `use-computer` cost.

**Cons:** Slower than hand-written Playwright; less flexible than full terminal access.

**API key:** `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `LLM_API_KEY` (mapped by model provider).

```bash
uv run harbor run -c configs/jobs/persona-browser-use-local.yaml
```

Oracle:

```bash
uv run harbor run -p tasks/web/books-interest-browser-use -a oracle
```

## Cocoa mode (AIO Sandbox)

**How it works:** The task Docker image is [`agent-infra/sandbox`](https://github.com/agent-infra/sandbox) (browser + shell + files on `localhost:8080`). [CocoaAgent](https://github.com/cocoabench/cocoa-agent) connects in-process with `skip_docker` — no second container. Persona is merged into the **instruction** (same slot as OpenHands / computer-1).

**Pros:** All-in-one digital agent without `use-computer`; no Docker socket mount; faster cold start than nested sandbox.

**Cons:** Heavier base image than Playwright-only tasks; task Dockerfiles should extend the AIO Sandbox image.

```bash
uv run harbor run -c configs/jobs/persona-cocoa-local.yaml
```

## CUA mode (Chromium + computer-use)

**How it works:** A real desktop browser window; each turn the model receives a **screenshot** and returns actions (`navigate`, `click`, `scroll`, …). Same family as `tasks/computer-use/notification-preferences/`.

**Pros:** Closest to end-user behavior; good for UX / friction studies.

**Cons:** Slower, costlier, less deterministic; needs `USE_COMPUTER_API_KEY` and `-e use-computer`.

```bash
export USE_COMPUTER_API_KEY=...
uv run harbor run \
  -a persona-computer-1 \
  -m anthropic/claude-sonnet-4-20250514 \
  --ak persona_path=personas/examples/persona_0042.yaml \
  -p tasks/web/books-interest-cua \
  -e use-computer
```

Oracle (writes submission file directly; still needs use-computer sandbox):

```bash
uv run harbor run -p tasks/web/books-interest-cua -a oracle -e use-computer
```

## What we do *not* treat as a web mode

| Approach | Status |
|----------|--------|
| [Skyvern](https://github.com/Skyvern-AI/skyvern) | No `persona-skyvern` — AGPL-3.0 does not fit this Apache-2.0 repo; use browser-use or CUA for vision-first browsing. |
| `curl` / `wget` only | Not a web interaction mode — no JS, no layout. OK for smoke, not documented as persona web browsing. |
| Mock HTML sidecar | Deprecated for MatrAIx web examples; use live URL tasks under `tasks/web/`. |

## Authoring a new live-web application

1. Choose a mode from the table above.
2. Reuse the submission JSON contract (or document a new one in the task README).
3. Set `network_mode = "public"` where the agent must reach the internet.
4. For Cocoa, use an AIO Sandbox base image in the task `Dockerfile` (see `books-interest-cocoa`).
5. Add **Suggested setup (non-binding)** in `tasks/.../README.md` — do not hard-code agent in `task.toml`.
6. Document URL stability and login requirements in README **Known limitations**.

## Reference tasks

| Task | Mode |
|------|------|
| `tasks/web/books-interest-playwright/` | Playwright + live URL |
| `tasks/web/books-interest-browser-use/` | browser-use + live URL |
| `tasks/web/books-interest-cocoa/` | Cocoa + live URL |
| `tasks/web/books-interest-cua/` | CUA + live URL |

See also [task-guide.md](./task-guide.md) and [choosing-an-agent.md](../environments/choosing-an-agent.md).
