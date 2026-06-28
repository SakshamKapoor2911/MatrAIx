# Ecommerce Platform Product Discovery

PersonaBench web/computer-use task with a task-specific hosted ecommerce storefront.
The persona agent browses a local shop UI and submits a self-reported product
choice after using the site.

## Application Host

| Component | Value |
| --- | --- |
| Web app sidecar | `ecommerce-web` |
| URL inside task | `http://ecommerce-web:8000/` |
| Interaction mode | Browser / computer-use |
| Output | `/app/output/ecommerce_interaction.json` |

The storefront is intentionally small and deterministic. It validates the
task-specific hosted web app pattern before introducing larger WebArena-derived
applications.

## Local Smoke

```bash
uv sync --extra computer-1
export ANTHROPIC_API_KEY=...
uv run harbor run -c configs/jobs/example-job-recipe/appSim-web-ecommerce-platform-local.yaml
```

Oracle:

```bash
uv run harbor run -p application/tasks/web-ecommerce-platform_product-discovery -a oracle
```

## Expected Submission

The persona agent should finish with a done action containing:

```json
{
  "selected_product_id": "desk-002",
  "selected_product_name": "FocusDesk Pro",
  "need_satisfaction": 8,
  "ease_of_use": 7,
  "overall_experience_rating": 8,
  "reason": "The comparison page made the tradeoffs clear."
}
```

`need_satisfaction`, `ease_of_use`, and `overall_experience_rating` are integer
ratings from 1 to 10.
