# Wiki Collaborator Runner Design

## Goal

Make each outbound wiki persona attribution package usable by collaborators who
receive only an assignment `.tar.gz`. The package should have one obvious
entrypoint:

```bash
./run_assignment.sh
```

That entrypoint should behave like a small installer and terminal dashboard. It
checks the local environment, helps the user pick Claude Code or Codex CLI,
persists that choice, runs the resumable attribution job, shows progress, and
validates `results.jsonl` before the collaborator returns it.

## Package Contract

`make_collab_package.py` will continue to create the worker-facing package. The
package will include:

- `assignment.json`
- `tasks.jsonl`
- `dimensions.json`
- `README.md`
- `run_assignment.sh`
- `collab_kit/`

The existing result contract remains unchanged. Collaborators return
`results.jsonl`. Owner-side validation and merge continue to use
`merge_collab_results.py`.

## Entrypoint Shape

`run_assignment.sh` will be a thin, portable launcher. It will:

- locate a usable Python runtime;
- prefer `uv run` if `uv` is available;
- fall back to `python3` or `python`;
- run `collab_kit/assignment_runner.py`;
- forward all CLI arguments.

The heavier logic will live in `assignment_runner.py` so it is easier to test
and keep cross-platform. The runner will use only the Python standard library in
the first version.

## Interactive Flow

Running `./run_assignment.sh` with no flags opens a terminal menu:

1. Environment check.
2. Backend setup.
3. Status.
4. Mock smoke test.
5. Real run or resume.
6. Validate current `results.jsonl`.
7. Quit.

The menu is a simple line-oriented TUI, not a curses full-screen UI. This keeps
it usable on macOS, Linux, WSL, SSH, and Git Bash-style terminals.

## Persisted Settings

The first real run asks the user to choose a backend:

- `claude-code-acp`
- `codex-acp`
- `mock`
- advanced external command backend

The choice, model, effort, jobs, and optional command overrides are saved in a
package-local config file such as `.wiki_collab_config.json`. On later launches,
the runner shows the current settings and asks whether to keep them or overwrite
them. Non-interactive flags can bypass prompts:

```bash
./run_assignment.sh --backend codex-acp --jobs 4 --effort high --yes
./run_assignment.sh --configure
./run_assignment.sh --status
```

## Environment And Subscription Checks

The runner checks:

- package files exist: `assignment.json`, `tasks.jsonl`, `dimensions.json`,
  `collab_kit/harness.py`, `collab_kit/conformance.py`;
- Python is new enough for the bundled code;
- `uv` availability, without requiring it;
- selected backend CLI availability;
- selected backend auth appears usable.

Backend auth checks should be conservative. For Claude and Codex CLI, the first
version can verify that the command exists and run a tiny non-destructive probe
where the CLI supports it. If a reliable auth probe is unavailable, the runner
reports that auth will be confirmed by the smoke or real run.

## Backend Defaults

Claude Code already has a bundled adapter through `claude_json_backend.py`.
Codex should get the same experience: `codex-acp` should work without asking the
collaborator to hand-write `WIKI_COLLAB_CODEX_CMD`. The kit will include a
`codex_json_backend.py` adapter, and `solver.py` will set default commands for
both Claude and Codex when the environment variables are absent.

Users can still override:

- `WIKI_COLLAB_CLAUDE_CMD`
- `WIKI_COLLAB_CODEX_CMD`
- `WIKI_COLLAB_OPENAI_CMD`
- `WIKI_COLLAB_ANTHROPIC_CMD`

The runner will display which command it will use before starting a real run.

## Quota And Resume

The existing checkpoint model remains the core quota strategy. The work unit is
`profile x category`; every successful unit is appended to
`results.jsonl.progress.jsonl`. If the backend hits quota, auth, network, or
parse errors, completed units stay done. The user can rerun:

```bash
./run_assignment.sh
```

and choose "Real run or resume". The runner skips completed units through the
existing `harness.py` behavior.

Partial `results.jsonl` may exist, but it is not complete until `harness.py`
reports all units done and conformance passes. The menu will show both unit
progress and fully completed profile count by calling the harness status path.

## Validation

The runner exposes validation as a first-class menu option and as a CLI command:

```bash
./run_assignment.sh --validate
```

This calls the bundled `conformance.py` against `results.jsonl`,
`dimensions.json`, and `tasks.jsonl`. A passing validation means the file is
ready to return, subject to owner-side identity/merge checks.

## Cross-Platform Policy

The supported fast path is Unix-like shells: macOS, Linux, WSL, and Git Bash.
The package remains Python-stdlib-only so Windows users can still run the Python
launcher directly:

```bash
python collab_kit/assignment_runner.py
```

`uv` is optional. If present, the shell launcher may use it to run Python with a
consistent interpreter, but the package must still work without network access
or dependency installation after unpacking.

## Testing

Tests will cover:

- `make_collab_package.py` includes `run_assignment.sh` and
  `collab_kit/assignment_runner.py` in the package directory and archive;
- package ignore rules do not include stale generated outputs;
- `assignment_runner.py --status` works on a tiny package before any run;
- `assignment_runner.py --backend mock --yes` executes a mock run and validates;
- first-run backend config is written and subsequent runs can reuse it;
- `solver.py` installs default commands for Claude and Codex when env vars are
  unset.

## Out Of Scope

- Sharing the owner SQLite database with collaborators.
- Replacing `merge_collab_results.py`.
- Requiring collaborators to clone the MatrAIx repository.
- Installing Claude Code, Codex CLI, or `uv` automatically through networked
  package managers. The runner may explain missing tools, but it should not
  mutate a collaborator machine beyond package-local config/progress files.
