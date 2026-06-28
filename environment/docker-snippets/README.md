# Docker Snippets

Shared Docker helper scripts for PersonaBench task images.

Harbor builds each task from its own `environment/` directory, so task
Dockerfiles cannot reliably `COPY` files from this shared directory. Keep the
canonical script here, then sync task-local copies with:

```bash
python scripts/sync_docker_snippets.py --write
```

CI should use:

```bash
python scripts/sync_docker_snippets.py --check
```

Current snippets:

- `install-claude-code.sh`: installs Claude Code, `uv`, and base runtime
  directories for `persona-claude-code` survey/chat task images.
