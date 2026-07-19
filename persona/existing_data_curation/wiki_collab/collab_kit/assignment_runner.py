#!/usr/bin/env python3
"""Assignment package runner.

This is the worker-facing entrypoint behind ../run_assignment.sh. It keeps the
package self-contained: verify immutable inputs, persist simple settings, run or
resume the bundled harness, and validate results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


KIT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = KIT_DIR.parent
SETTINGS_PATH = PACKAGE_ROOT / ".wiki_collab_settings.yaml"
ACTIVE_RUN_PATH = PACKAGE_ROOT / ".wiki_collab_active_run.yaml"
RESULTS_PATH = PACKAGE_ROOT / "results.jsonl"
PROGRESS_PATH = PACKAGE_ROOT / "results.jsonl.progress.jsonl"

DEFAULTS = {
    "backend": "codex-acp",
    "model": "gpt-5.5",
    "effort": "high",
    "jobs": "4",
    "command_override": "",
}
PROVENANCE_KEYS = ("backend", "model", "effort", "command_override")
DIRECT_BACKEND_CHOICES = ("codex-acp", "claude-code-acp", "mock")

BACKEND_CHOICES = [
    ("codex-acp", "Codex CLI / ChatGPT subscription"),
    ("claude-code-acp", "Claude Code CLI / Claude subscription"),
]
MODEL_BY_BACKEND = {
    "codex-acp": "gpt-5.5",
    "claude-code-acp": "claude-opus-4-8",
    "mock": "mock-model",
}
EFFORT_CHOICES_BY_BACKEND = {
    # Codex config supports these reasoning effort values; xhigh is model-dependent.
    "codex-acp": [
        ("high", "high - deeper reasoning for harder extraction"),
        ("medium", "medium - balanced token use"),
        ("xhigh", "xhigh - deepest Codex reasoning when supported"),
    ],
    # Claude Code --effort supports these values for Opus 4.8.
    "claude-code-acp": [
        ("high", "high - Opus 4.8 default"),
        ("medium", "medium - lower token use"),
        ("xhigh", "xhigh - deeper reasoning"),
        ("max", "max - deepest, can overthink"),
    ],
    "mock": [
        ("high", "high - smoke-test placeholder"),
    ],
}
DEFAULT_EFFORT_BY_BACKEND = {
    "codex-acp": "high",
    "claude-code-acp": "high",
    "mock": "high",
}
JOB_CHOICES = [
    ("4", "4 parallel calls"),
    ("2", "2 parallel calls"),
    ("6", "6 parallel calls"),
    ("8", "8 parallel calls"),
    ("1", "1 call at a time"),
]
MAX_JOBS = 32  # upper bound for parallel model calls (quota/rate-limit safety)
HARNESS_VERSION = "1.0.0"


def _supports_color() -> bool:
    """Emit ANSI color only when it is safe: an interactive stdout, not disabled
    via NO_COLOR, and not a dumb terminal. Off under pipes/redirects/tests."""
    return (
        sys.stdout.isatty()
        and os.environ.get("NO_COLOR") is None
        and os.environ.get("TERM", "") not in ("", "dumb")
    )


_COLOR = _supports_color()


def _paint(code: str, text: str) -> str:
    return f"\x1b[{code}m{text}\x1b[0m" if _COLOR else text


def _bold(t: str) -> str:
    return _paint("1", t)


def _dim(t: str) -> str:
    return _paint("2", t)


def _cyan(t: str) -> str:
    return _paint("1;36", t)


def _green(t: str) -> str:
    return _paint("32", t)


def _yellow(t: str) -> str:
    return _paint("33", t)


def _red(t: str) -> str:
    return _paint("31", t)


def _rule(width: int = 48) -> str:
    return _dim("─" * width)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _yaml_quote(value: str) -> str:
    if value == "" or any(ch in value for ch in ":#\"'\n"):
        return json.dumps(value)
    return value


def read_flat_yaml(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = value.strip('"')
        data[key.strip()] = str(value)
    return data


def write_flat_yaml(path: Path, settings: dict[str, Any]) -> None:
    lines = [f"{key}: {_yaml_quote(str(value))}" for key, value in settings.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_manifest(root: Path = PACKAGE_ROOT) -> dict[str, Any]:
    path = root / "package_manifest.json"
    if not path.exists():
        raise FileNotFoundError("missing package_manifest.json")
    return json.loads(path.read_text(encoding="utf-8"))


def verify_manifest(root: Path = PACKAGE_ROOT) -> tuple[list[str], list[str]]:
    manifest = load_manifest(root)
    errors: list[str] = []
    warnings: list[str] = []
    files = manifest.get("files", {})
    if not isinstance(files, dict):
        return ["package_manifest.json has no files map"], warnings

    for rel, meta in files.items():
        path = root / rel
        mode = meta.get("mode")
        expected = meta.get("sha256")
        if not path.exists():
            msg = f"{rel}: manifest mismatch (missing file)"
            if mode == "editable":
                warnings.append(msg)
            else:
                errors.append(msg)
            continue
        actual = sha256_file(path)
        if expected != actual:
            msg = f"{rel}: manifest mismatch (expected {expected}, got {actual})"
            if mode == "editable":
                warnings.append(msg)
            else:
                errors.append(msg)
    return errors, warnings


def manifest_sha256(root: Path = PACKAGE_ROOT) -> str:
    return sha256_file(root / "package_manifest.json")


def settings_hash(settings: dict[str, Any]) -> str:
    payload = {key: str(settings.get(key, "")) for key in PROVENANCE_KEYS}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def progress_exists(root: Path = PACKAGE_ROOT) -> bool:
    return (root / "results.jsonl.progress.jsonl").exists()


def normalize_settings(settings: dict[str, Any]) -> dict[str, str]:
    normalized = {key: str(value) for key, value in {**DEFAULTS, **settings}.items()}
    backend = normalized.get("backend", DEFAULTS["backend"])
    if backend not in DIRECT_BACKEND_CHOICES:
        backend = DEFAULTS["backend"]
    normalized["backend"] = backend

    if backend in {"codex-acp", "claude-code-acp"}:
        normalized["model"] = MODEL_BY_BACKEND[backend]
    elif backend == "mock" and normalized.get("model") in {
        "",
        DEFAULTS["model"],
        MODEL_BY_BACKEND["codex-acp"],
        MODEL_BY_BACKEND["claude-code-acp"],
    }:
        normalized["model"] = MODEL_BY_BACKEND["mock"]

    effort_values = {value for value, _description in EFFORT_CHOICES_BY_BACKEND[backend]}
    if normalized.get("effort") not in effort_values:
        normalized["effort"] = DEFAULT_EFFORT_BY_BACKEND[backend]
    try:
        jobs_n = int(normalized.get("jobs", DEFAULTS["jobs"]))
    except (TypeError, ValueError):
        jobs_n = int(DEFAULTS["jobs"])
    normalized["jobs"] = str(max(1, min(MAX_JOBS, jobs_n)))
    normalized["command_override"] = normalized.get("command_override", "")
    return normalized


def configured_settings(args: argparse.Namespace) -> dict[str, str]:
    settings = {**DEFAULTS, **read_flat_yaml(SETTINGS_PATH)}
    previous_backend = settings.get("backend")
    for key in ("backend", "model", "effort", "command_override"):
        value = getattr(args, key, None)
        if value is not None:
            settings[key] = str(value)
    if args.jobs is not None:
        settings["jobs"] = str(args.jobs)
    if args.backend is not None and args.model is None and settings.get("backend") != previous_backend:
        settings["model"] = MODEL_BY_BACKEND.get(settings["backend"], settings.get("model", ""))
    if args.backend is not None and args.effort is None and settings.get("backend") != previous_backend:
        settings["effort"] = DEFAULT_EFFORT_BY_BACKEND.get(settings["backend"], settings.get("effort", "high"))
    return normalize_settings(settings)


def build_assignment_provenance(
    root: Path,
    settings: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    manifest = load_manifest(root)
    files = manifest.get("files", {})
    assignment = dict(manifest.get("assignment", {}))
    assignment.update(
        {
            "tasks_sha256": files.get("tasks.jsonl", {}).get("sha256"),
            "dimensions_sha256": files.get("dimensions.json", {}).get("sha256"),
            "package_manifest_sha256": manifest_sha256(root),
            "settings_hash": settings_hash(settings),
            "editable_warnings": warnings,
        }
    )
    return assignment


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> int:
    # Flush our own buffered stdout/stderr BEFORE spawning the child, so our
    # lines (Integrity: PASS, errors) don't get reordered after the child's
    # output when stdout is piped/redirected (non-TTY block buffering).
    sys.stdout.flush()
    sys.stderr.flush()
    proc = subprocess.run(cmd, cwd=cwd, env=env)
    return proc.returncode


def ensure_integrity(root: Path = PACKAGE_ROOT) -> list[str]:
    try:
        errors, warnings = verify_manifest(root)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    for warning in warnings:
        print(f"{_yellow('WARN')}  {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"{_red('ERROR')} {error}", file=sys.stderr)
        raise SystemExit(1)
    return warnings


def run_status(root: Path = PACKAGE_ROOT) -> int:
    ensure_integrity(root)
    print(f"Integrity: {_green('PASS')}")
    return _run(
        [
            sys.executable,
            "harness.py",
            "--tasks",
            "../tasks.jsonl",
            "--dimensions",
            "../dimensions.json",
            "--out",
            "../results.jsonl",
            "--status",
        ],
        cwd=root / "collab_kit",
    )


def _completion(root: Path) -> tuple[int, int]:
    """(units_done, total) from tasks.jsonl + dimensions.json + the checkpoint.

    Lets --validate tell "format is valid" apart from "the run actually finished".
    Returns (0, 0) when it can't be determined (so callers skip the check)."""
    try:
        tasks = [
            json.loads(line)
            for line in (root / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        dims = json.loads((root / "dimensions.json").read_text(encoding="utf-8"))
        cats: list[str] = []
        seen: set[str] = set()
        for d in dims:
            c = str(d.get("category", "_"))
            if c not in seen:
                seen.add(c)
                cats.append(c)
        total = len(tasks) * len(cats)
        done: set[tuple[int, str]] = set()
        prog = root / "results.jsonl.progress.jsonl"
        if prog.exists():
            for line in prog.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                gi, cat = rec.get("global_idx"), rec.get("category")
                if isinstance(gi, int) and isinstance(cat, str):
                    done.add((gi, cat))
        return len(done), total
    except Exception:
        return 0, 0


def run_validate(root: Path = PACKAGE_ROOT) -> int:
    ensure_integrity(root)
    if not (root / "results.jsonl").exists():
        print("ERROR: results.jsonl does not exist yet", file=sys.stderr)
        return 1
    rc = _run(
        [
            sys.executable,
            "conformance.py",
            "--results",
            "../results.jsonl",
            "--dimensions",
            "../dimensions.json",
            "--tasks",
            "../tasks.jsonl",
        ],
        cwd=root / "collab_kit",
    )
    # The format can be valid while the run is unfinished (every task gets a
    # record, some with empty fields), so conformance alone says PASS. Cross-check
    # the checkpoint so a half-finished run is not mistaken for ready-to-send.
    done, total = _completion(root)
    if total and done < total:
        print(
            f"WARN: results are INCOMPLETE — {done}/{total} units done. "
            "Resume and finish the run before sending results.jsonl.",
            file=sys.stderr,
        )
        return 1
    return rc


def _write_active_run(settings: dict[str, Any]) -> None:
    write_flat_yaml(
        ACTIVE_RUN_PATH,
        {
            "settings_hash": settings_hash(settings),
            "backend": settings.get("backend", ""),
            "model": settings.get("model", ""),
            "effort": settings.get("effort", ""),
            "command_override": settings.get("command_override", ""),
        },
    )


def _progress_has_legacy_rows(path: Path) -> bool:
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec.get("run"), dict):
            return True
    return False


def _run_from_active_metadata(
    active: dict[str, str],
    *,
    warnings: list[str],
) -> dict[str, Any] | None:
    if not (active.get("backend") and active.get("model") and active.get("effort")):
        return None
    settings = {**DEFAULTS, **active}
    return {
        "backend": active.get("backend"),
        "model": active.get("model"),
        "effort": active.get("effort"),
        "runner_version": HARNESS_VERSION,
        "assignment": build_assignment_provenance(PACKAGE_ROOT, settings, warnings),
    }


def _backfill_legacy_progress_run(path: Path, run: dict[str, Any]) -> None:
    lines: list[str] = []
    changed = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            lines.append(raw)
            continue
        if not isinstance(rec.get("run"), dict):
            rec["run"] = run
            changed = True
        lines.append(json.dumps(rec, ensure_ascii=False))
    if changed:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _check_progress_settings(
    settings: dict[str, Any],
    *,
    restart: bool,
    warnings: list[str],
) -> None:
    if restart:
        return
    if not PROGRESS_PATH.exists():
        return
    active = read_flat_yaml(ACTIVE_RUN_PATH)
    if not _progress_has_legacy_rows(PROGRESS_PATH):
        return
    legacy_run = _run_from_active_metadata(active, warnings=warnings)
    if legacy_run is None:
        print(
            "ERROR: existing progress has no active-run metadata; rerun with --restart "
            "to avoid mixing backend/model/effort provenance.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    _backfill_legacy_progress_run(PROGRESS_PATH, legacy_run)


def run_harness(settings: dict[str, Any], *, restart: bool = False, smoke: bool = False) -> int:
    warnings = ensure_integrity(PACKAGE_ROOT)
    # A smoke test must NOT touch the real run: it writes to a throwaway output
    # and leaves the persistent checkpoint, settings, and active-run untouched.
    out_rel = "../.smoke_results.jsonl" if smoke else "../results.jsonl"
    if not smoke:
        _check_progress_settings(settings, restart=restart, warnings=warnings)
        write_flat_yaml(SETTINGS_PATH, settings)
        _write_active_run(settings)

    env = os.environ.copy()
    if settings.get("command_override"):
        backend = settings.get("backend", "")
        if backend == "claude-code-acp":
            env["WIKI_COLLAB_CLAUDE_CMD"] = settings["command_override"]
        elif backend == "codex-acp":
            env["WIKI_COLLAB_CODEX_CMD"] = settings["command_override"]
    env["WIKI_COLLAB_ASSIGNMENT_PROVENANCE"] = json.dumps(
        build_assignment_provenance(PACKAGE_ROOT, settings, warnings),
        ensure_ascii=False,
        sort_keys=True,
    )

    cmd = [
        sys.executable,
        "harness.py",
        "--tasks",
        "../tasks.jsonl",
        "--dimensions",
        "../dimensions.json",
        "--out",
        out_rel,
        "--backend",
        str(settings["backend"]),
        "--model",
        str(settings["model"]),
        "--effort",
        str(settings["effort"]),
        "--jobs",
        str(settings["jobs"]),
    ]
    if restart or smoke:  # a smoke run is always fresh
        cmd.append("--restart")
    rc = _run(cmd, cwd=KIT_DIR, env=env)
    if smoke:
        for p in (
            PACKAGE_ROOT / ".smoke_results.jsonl",
            PACKAGE_ROOT / ".smoke_results.jsonl.progress.jsonl",
        ):
            try:
                p.unlink()
            except FileNotFoundError:
                pass
    return rc


def print_environment(root: Path = PACKAGE_ROOT) -> int:
    ensure_integrity(root)
    settings = normalize_settings(read_flat_yaml(SETTINGS_PATH))
    print(f"Integrity: {_green('PASS')}")
    print(f"Python: {sys.executable}")
    print(f"Package: {root}")
    print(f"Selected backend: {settings['backend']} (model={settings['model']}, effort={settings['effort']})")
    return 0 if _check_backend_environment(settings["backend"]) else 1


def _run_probe(label: str, cmd: list[str], *, timeout: int = 30) -> bool:
    binary = cmd[0]
    if shutil.which(binary) is None:
        print(f"{label}: FAIL ({binary} not found on PATH)")
        return False
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception as exc:
        print(f"{label}: FAIL ({exc})")
        return False
    if proc.returncode == 0:
        print(f"{label}: {_green('PASS')}")
        return True
    detail = (proc.stderr or proc.stdout).strip().splitlines()
    suffix = f" ({detail[-1]})" if detail else ""
    print(f"{label}: {_red('FAIL')}{suffix}")
    return False


def _check_backend_environment(backend: str) -> bool:
    if backend == "mock":
        print("Mock backend: PASS (no external CLI/auth required)")
        return True
    if backend == "codex-acp":
        return _run_probe("Codex CLI", ["codex", "doctor", "--summary", "--ascii", "--no-color"])
    if backend == "claude-code-acp":
        return _run_probe("Claude Code CLI", ["claude", "doctor"])
    print(f"Backend check: FAIL (unsupported backend {backend!r})")
    return False


def _select_option(
    label: str,
    choices: list[tuple[str, str]],
    *,
    default_value: str | None = None,
) -> str:
    values = [value for value, _description in choices]
    try:
        default_index = values.index(default_value or "") + 1
    except ValueError:
        default_index = 1
    while True:
        print(f"\n{label}:")
        for idx, (value, description) in enumerate(choices, start=1):
            marker = " (default)" if idx == default_index else ""
            print(f"  {idx}. {value} - {description}{marker}")
        raw = input(f"Select {label.lower()} [1-{len(choices)}; default {default_index}]: ").strip()
        if not raw:
            return choices[default_index - 1][0]
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(choices):
                return choices[idx - 1][0]
        print(f"Please choose a number from 1 to {len(choices)}.")


def _prompt_jobs(default: str) -> str:
    """Ask for the number of parallel jobs as a free-typed integer (1..MAX_JOBS).

    Enter keeps the default; the common preset values are shown only as a hint.
    Re-prompts on anything out of range so the value is always usable."""
    try:
        default_n = max(1, min(MAX_JOBS, int(default)))
    except (TypeError, ValueError):
        default_n = int(DEFAULTS["jobs"])
    common = ", ".join(sorted({value for value, _ in JOB_CHOICES}, key=int))
    print(f"\n{_bold('Parallel jobs')} — how many model calls run at once.")
    print(_dim(f"  Type any whole number 1-{MAX_JOBS} (common: {common}). "
               "Higher = faster but heavier on your quota/CPU."))
    while True:
        raw = input(f"Number of parallel jobs [default {default_n}]: ").strip()
        if not raw:
            return str(default_n)
        if raw.isdigit() and 1 <= int(raw) <= MAX_JOBS:
            return str(int(raw))
        print(f"Please enter a whole number from 1 to {MAX_JOBS}.")


def _normalize_interactive_settings(settings: dict[str, str]) -> dict[str, str]:
    normalized = normalize_settings(settings)
    if normalized["backend"] == "mock":
        normalized["backend"] = DEFAULTS["backend"]
        normalized["model"] = MODEL_BY_BACKEND[normalized["backend"]]
        normalized["effort"] = DEFAULT_EFFORT_BY_BACKEND[normalized["backend"]]
    normalized["command_override"] = ""
    return normalized


def configure_interactive(existing: dict[str, str]) -> dict[str, str]:
    settings = _normalize_interactive_settings({**DEFAULTS, **existing})
    if existing:
        # Show the saved values, which are the wizard's defaults. Pressing Enter
        # at each step keeps the current value — no separate "Keep these
        # settings? [Y/n]" gate that would cost an extra keypress.
        print("Current settings (press Enter at each step to keep the value):")
        for key in ("backend", "model", "effort", "jobs"):
            print(f"  {key}: {settings.get(key, '')}")

    backend = _select_option("Backend", BACKEND_CHOICES, default_value=settings.get("backend"))
    settings["backend"] = backend
    settings["model"] = MODEL_BY_BACKEND[backend]
    print(f"Model: {settings['model']}")
    settings["effort"] = _select_option(
        f"Effort for {backend}",
        EFFORT_CHOICES_BY_BACKEND[backend],
        default_value=settings.get("effort") or DEFAULT_EFFORT_BY_BACKEND[backend],
    )
    settings["jobs"] = _prompt_jobs(settings.get("jobs") or DEFAULTS["jobs"])
    settings["command_override"] = ""
    write_flat_yaml(SETTINGS_PATH, settings)
    print(f"Wrote settings -> {SETTINGS_PATH}")
    return settings


def interactive_menu() -> int:
    if not sys.stdin.isatty():
        print(
            "No interactive terminal detected. Use direct commands, e.g.:\n"
            "  ./run_assignment.sh --status\n"
            "  ./run_assignment.sh --backend codex-acp --effort high --jobs 4 --yes --run\n"
            "  ./run_assignment.sh --backend claude-code-acp --effort high --jobs 6 --yes --run\n"
            "  ./run_assignment.sh --validate",
            file=sys.stderr,
        )
        return 2
    settings = read_flat_yaml(SETTINGS_PATH)
    items = [
        ("1", "Environment check"),
        ("2", "Configure backend/model/effort"),
        ("3", "Status"),
        ("4", "Mock smoke test"),
        ("5", "Real run / resume"),
        ("6", "Validate results"),
        ("7", "Quit"),
    ]
    while True:
        print()
        print(_bold(_cyan("  MatrAIx wiki assignment runner")))
        print(_rule())
        for num, label in items:
            print(f"  {_bold(_cyan(num))}  {label}")
        print(_rule())
        choice = input(_bold("Select [1-7]: ")).strip() or "1"
        # Divider so the action's output is visually separated from the menu.
        print(_rule())
        if choice == "1":
            print_environment(PACKAGE_ROOT)
        elif choice == "2":
            settings = configure_interactive(settings)
        elif choice == "3":
            run_status(PACKAGE_ROOT)
        elif choice == "4":
            mock_settings = {**DEFAULTS, **settings, "backend": "mock", "model": "mock-model"}
            rc = run_harness(mock_settings, smoke=True)  # throwaway: never touches the real run
            if rc != 0:
                return rc
        elif choice == "5":
            # Run straight away with the saved settings (one keypress: "5").
            # Configure only when nothing is saved yet; use option 2 to change.
            if not settings:
                settings = configure_interactive(settings)
            run_settings = _normalize_interactive_settings(settings)
            print(
                _green(_bold("Starting real run: "))
                + f"backend={run_settings['backend']} "
                f"model={run_settings['model']} effort={run_settings['effort']} "
                f"jobs={run_settings['jobs']}  " + _dim("(option 2 to change settings)")
            )
            rc = run_harness(run_settings, restart=False)
            if rc != 0:
                return rc
        elif choice == "6":
            rc = run_validate(PACKAGE_ROOT)
            if rc != 0:
                return rc
        elif choice == "7":
            return 0
        else:
            print("Please choose a number from 1 to 7.")



def _confirm_real_run(settings: dict[str, Any], *, assume_yes: bool) -> bool:
    """Gate a real (non-mock) run so an accidental `--run` does not silently
    spend a subscription. `--yes` (or a mock backend) skips the prompt; a
    non-interactive shell without `--yes` is refused rather than run blindly."""
    backend = str(settings.get("backend", ""))
    if assume_yes or backend == "mock":
        return True
    if not sys.stdin.isatty():
        print(
            f"Refusing to start a real {backend} run without confirmation. "
            "Re-run with --yes to proceed non-interactively (or --backend mock to smoke test).",
            file=sys.stderr,
        )
        return False
    prompt = (
        f"About to run backend={backend} "
        f"(model={settings.get('model', '')}, effort={settings.get('effort', '')}) "
        "using your subscription/credentials. Continue? [y/N] "
    )
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=DIRECT_BACKEND_CHOICES)
    parser.add_argument("--model")
    parser.add_argument(
        "--effort",
        choices=sorted({value for choices in EFFORT_CHOICES_BY_BACKEND.values() for value, _ in choices}),
    )
    parser.add_argument("--jobs", type=int)
    parser.add_argument("--command-override", default=None)
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--configure", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--restart", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = configured_settings(args)
    if args.configure:
        ensure_integrity(PACKAGE_ROOT)
        write_flat_yaml(SETTINGS_PATH, settings)
        print(f"Wrote settings -> {SETTINGS_PATH}")
        return 0
    if args.status:
        return run_status(PACKAGE_ROOT)
    if args.validate:
        return run_validate(PACKAGE_ROOT)
    if args.run:
        if not _confirm_real_run(settings, assume_yes=args.yes):
            print("Aborted — no run started.", file=sys.stderr)
            return 1
        return run_harness(settings, restart=args.restart)
    return interactive_menu()


if __name__ == "__main__":
    raise SystemExit(main())
