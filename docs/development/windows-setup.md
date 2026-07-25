# Windows Development Setup

## Prerequisites

- Windows 10/11 with PowerShell 5.1+
- Git for Windows
- Python 3.12+
- UV package manager (`powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`)
- Docker Desktop for Windows (enable WSL2 backend)

## Common Issues

### .venv/lib64 symlink

The `.venv/lib64` directory doesn't exist on Windows (it is a symlink created by `uv` on Linux). If a tool crashes during recursive `.venv` traversal, either:
- Add `.venv/lib64` to `.gitignore`
- Guard recursive walks with `if sys.platform == "win32" and "lib64" in str(path): continue`

### Path separators

Always use `PurePosixPath` for container paths and `Path.as_posix()` for host-to-container path mapping. On Windows, `str(Path(...))` produces backslash paths (`C:\Users\...`) which break container commands expecting forward slashes.

### Docker

Enable WSL2 backend in Docker Desktop settings. Use `docker-compose-windows-keepalive.yaml` for Windows-specific Docker requirements.

### PYTHONPATH

When running harbor or playground components, set PYTHONPATH in this order:

```powershell
$env:PYTHONPATH="<repo>\environment\agents;<repo>\src;<repo>\environment\runtime"
```

### Harbor CLI

The harbor CLI works on Windows for non-Docker operations. Docker-based runs require WSL2.

### Known Working Configurations

| Component | Status | Notes |
|-----------|--------|-------|
| harbor CLI (non-Docker) | Working | Batch runs, analysis, upload |
| harbor Docker backend | Working | Requires WSL2 backend |
| Playground UI backend | Working | Run via uvicorn on port 8765 |
| Playground frontend | Working | Run via npm run dev |
| Persona generation | Working | Python scripts |
| PDF report generation | Working | Playwright headless |
| GitHub CLI (gh) | Working | Use --body-file to avoid backtick mangling |
| Lambda SSH remote runner | Working | Requires WSL2 for SSH agent |
