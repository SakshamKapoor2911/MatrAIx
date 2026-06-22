# MatrAIx persona source exports

Optional upstream persona exports for one-off conversion experiments. The primary dev pool is generated locally:

```bash
uv run python persona/scripts/generate_dev_personas.py --count 2000 --seed 42
```

Output: `persona/datasets/bench-dev-2000/`.
