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
import platform
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
    "backend": "mock",
    "model": "mock-model",
    "effort": "high",
    "jobs": "4",
    "command_override": "",
}
PROVENANCE_KEYS = ("backend", "model", "effort", "command_override")


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


def configured_settings(args: argparse.Namespace) -> dict[str, str]:
    settings = {**DEFAULTS, **read_flat_yaml(SETTINGS_PATH)}
    for key in ("backend", "model", "effort", "command_override"):
        value = getattr(args, key, None)
        if value is not None:
            settings[key] = str(value)
    if args.jobs is not None:
        settings["jobs"] = str(args.jobs)
    return settings


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
        print(f"WARN  {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        raise SystemExit(1)
    return warnings


def run_status(root: Path = PACKAGE_ROOT) -> int:
    ensure_integrity(root)
    print("Integrity: PASS")
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
            "Finish the run (re-run the same command) before sending results.jsonl.",
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


def _check_progress_settings(settings: dict[str, Any], *, restart: bool) -> None:
    if restart:
        return
    if not PROGRESS_PATH.exists():
        return
    active = read_flat_yaml(ACTIVE_RUN_PATH)
    active_hash = active.get("settings_hash")
    current_hash = settings_hash(settings)
    if active_hash and active_hash != current_hash:
        print(
            "ERROR: existing progress was created with different backend/model/effort; "
            "rerun with the previous settings or pass --restart.",
            file=sys.stderr,
        )
        raise SystemExit(1)


def run_harness(settings: dict[str, Any], *, restart: bool = False, smoke: bool = False) -> int:
    warnings = ensure_integrity(PACKAGE_ROOT)
    # A smoke test must NOT touch the real run: it writes to a throwaway output
    # and leaves the persistent checkpoint, settings, and active-run untouched.
    out_rel = "../.smoke_results.jsonl" if smoke else "../results.jsonl"
    if not smoke:
        _check_progress_settings(settings, restart=restart)
        write_flat_yaml(SETTINGS_PATH, settings)
        _write_active_run(settings)

    env = os.environ.copy()
    if settings.get("command_override"):
        backend = settings.get("backend", "")
        if backend == "claude-code-acp":
            env["WIKI_COLLAB_CLAUDE_CMD"] = settings["command_override"]
        elif backend == "codex-acp":
            env["WIKI_COLLAB_CODEX_CMD"] = settings["command_override"]
        elif backend == "openai-api":
            env["WIKI_COLLAB_OPENAI_CMD"] = settings["command_override"]
        elif backend == "anthropic-api":
            env["WIKI_COLLAB_ANTHROPIC_CMD"] = settings["command_override"]
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
    print("Integrity: PASS")
    print(f"Python: {sys.executable}")
    uv = shutil.which("uv")
    print(f"uv: {uv or 'not found'}")
    print(f"Package: {root}")
    return 0


def install_uv(*, assume_yes: bool = False) -> int:
    existing = shutil.which("uv")
    if existing:
        print(f"uv: {existing} (already installed)")
        return 0
    if not assume_yes:
        answer = input("uv is not installed. Install it now? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Continuing without uv; the bundled runner works with python3.")
            return 0

    print(f"Platform: {platform.system()} {platform.machine()}")
    curl = shutil.which("curl")
    wget = shutil.which("wget")
    if curl or wget:
        if curl:
            cmd = f"{curl} -LsSf https://astral.sh/uv/install.sh | sh"
        else:
            cmd = f"{wget} -qO- https://astral.sh/uv/install.sh | sh"
        print("Installing uv with the official standalone installer...")
        rc = subprocess.run(cmd, shell=True, check=False).returncode
        if rc == 0:
            print("uv installer finished. Open a new shell if uv is not immediately on PATH.")
            return 0
        print("uv standalone installer failed; trying pip --user.")

    pip_cmd = [sys.executable, "-m", "pip", "install", "--user", "uv"]
    print("Installing uv with pip --user...")
    rc = subprocess.run(pip_cmd, check=False).returncode
    if rc == 0:
        print("uv pip install finished. Open a new shell if uv is not immediately on PATH.")
        return 0
    print("Could not install uv automatically. Install manually from https://docs.astral.sh/uv/")
    print("Continuing without uv is okay; this package only requires Python 3.")
    return 1


def _prompt(defaults: dict[str, str], key: str, label: str) -> str:
    default = defaults.get(key, "")
    raw = input(f"{label} [{default}]: ").strip()
    return raw or default


def configure_interactive(existing: dict[str, str]) -> dict[str, str]:
    settings = {**DEFAULTS, **existing}
    if existing:
        print("Current settings:")
        for key in ("backend", "model", "effort", "jobs", "command_override"):
            print(f"  {key}: {settings.get(key, '')}")
        answer = input("Keep these settings? [Y/n] ").strip().lower()
        if answer in {"", "y", "yes"}:
            return settings

    print("Choose backend: claude-code-acp, codex-acp, mock, openai-api, anthropic-api")
    settings["backend"] = _prompt(settings, "backend", "Backend")
    settings["model"] = _prompt(settings, "model", "Model")
    settings["effort"] = _prompt(settings, "effort", "Effort")
    settings["jobs"] = _prompt(settings, "jobs", "Parallel jobs")
    settings["command_override"] = _prompt(settings, "command_override", "Command override")
    write_flat_yaml(SETTINGS_PATH, settings)
    print(f"Wrote settings -> {SETTINGS_PATH}")
    return settings


def interactive_menu() -> int:
    if not sys.stdin.isatty():
        print(
            "No interactive terminal detected. Use direct commands, e.g.:\n"
            "  ./run_assignment.sh --status\n"
            "  ./run_assignment.sh --backend mock --yes --run\n"
            "  ./run_assignment.sh --backend claude-code-acp --yes --run\n"
            "  ./run_assignment.sh --validate",
            file=sys.stderr,
        )
        return 2
    settings = read_flat_yaml(SETTINGS_PATH)
    while True:
        print("\nMatrAIx wiki assignment runner")
        print("1. Environment check")
        print("2. uv check / install")
        print("3. Configure settings")
        print("4. Status")
        print("5. Mock smoke test")
        print("6. Real run / resume")
        print("7. Validate results")
        print("8. Quit")
        choice = input("Select [1-8]: ").strip() or "1"
        if choice == "1":
            print_environment(PACKAGE_ROOT)
        elif choice == "2":
            install_uv()
        elif choice == "3":
            settings = configure_interactive(settings)
        elif choice == "4":
            run_status(PACKAGE_ROOT)
        elif choice == "5":
            mock_settings = {**DEFAULTS, **settings, "backend": "mock", "model": "mock-model"}
            rc = run_harness(mock_settings, smoke=True)  # throwaway: never touches the real run
            if rc != 0:
                return rc
        elif choice == "6":
            settings = configure_interactive(settings)
            rc = run_harness(settings, restart=False)
            if rc != 0:
                return rc
        elif choice == "7":
            rc = run_validate(PACKAGE_ROOT)
            if rc != 0:
                return rc
        elif choice == "8":
            return 0
        else:
            print("Please choose a number from 1 to 8.")



def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend")
    parser.add_argument("--model")
    parser.add_argument("--effort")
    parser.add_argument("--jobs", type=int)
    parser.add_argument("--command-override", default=None)
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--configure", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--restart", action="store_true")
    parser.add_argument("--install-uv", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = configured_settings(args)
    if args.configure:
        ensure_integrity(PACKAGE_ROOT)
        write_flat_yaml(SETTINGS_PATH, settings)
        print(f"Wrote settings -> {SETTINGS_PATH}")
        return 0
    if args.install_uv:
        return install_uv(assume_yes=args.yes)
    if args.status:
        return run_status(PACKAGE_ROOT)
    if args.validate:
        return run_validate(PACKAGE_ROOT)
    if args.run:
        return run_harness(settings, restart=args.restart)
    return interactive_menu()


if __name__ == "__main__":
    raise SystemExit(main())
