# Example Job Recipes

Run these recipes from the repository root with:

```bash
uv run harbor run -c configs/jobs/example-job-recipe/<recipe>.yaml
```

The recipes use the checked-in sample persona:

```text
persona/datasets/bench-dev-sample/persona_0042.yaml
```

Included recipes:

- `harbor-smoke-local.yaml`
- `appSim-example-survey-local.yaml`
- `appSim-example-chat-local.yaml`
- `appSim-example-debug-local.yaml`
- `appSim-example-web-playwright-local.yaml`
- `appSim-example-web-browser-use-local.yaml`
- `appSim-example-web-cocoa-local.yaml`
- `appSim-example-web-linux-cua-local.yaml`
- `appSim-example-computer-use-linux-local.yaml`
- `appSim-example-computer-use-macos-local.yaml`
- `appSim-example-computer-use-ios-local.yaml`

Some recipes require API keys, local Docker, use-computer, Apple container
runtime support, or browser/Cocoa-specific task images. The recipes are kept as
small runnable entrypoints; generated outputs belong under local ignored
`jobs/`, not in git.

`harbor-smoke-local.yaml` uses the generic `examples/tasks/hello-world` task and
the built-in `oracle` agent, so it is the preferred no-API-key runtime smoke
recipe.
