"""Score an OS-app trial on the Playground host when the sandbox did not.

Harbor's primary verifier path executes ``tests/test.sh`` inside the sandbox.
Some computer-use environments (notably iOS) never produce ``verifier/reward.*``
even after the agent finished and artifacts were downloaded — the sandbox exec
channel simply cannot run the host-native verifier script.

Those verifiers only read already-collected submission files, so the same
``tests/test.sh`` can be executed on this machine against the trial's
downloaded artifacts. Artifact source paths and timeouts come from the task's
``task.toml``; the host path under ``trial/artifacts/`` follows Harbor's
``source_relative_path`` mapping.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tomllib
import uuid
from pathlib import Path, PurePosixPath
from threading import Lock

_LOCKS: dict[str, Lock] = {}
_LOCKS_GUARD = Lock()

_REWARD_FILENAMES = ("reward.txt", "reward.json")
_MISSING_REWARD_EXCEPTION = "RewardFileNotFoundError"
_DEFAULT_TIMEOUT_SEC = 120.0


def _lock_for(key: str) -> Lock:
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = Lock()
            _LOCKS[key] = lock
        return lock


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def source_relative_path(source: str) -> PurePosixPath:
    """Map a container artifact source to its path under ``trial/artifacts/``.

    Mirrors Harbor's ``harbor.models.task.artifacts.source_relative_path`` so
    host scoring looks in the same place downloads landed.
    """
    parts = [
        part for part in PurePosixPath(source).parts if part not in ("", "/", "..")
    ]
    return PurePosixPath(*parts) if parts else PurePosixPath(".")


def _is_absolute_source(path: str) -> bool:
    return path.startswith("/") or (len(path) >= 3 and path[1] == ":" and path[0].isalpha())


def _task_path_from_trial(trial_dir: Path) -> str | None:
    config_path = trial_dir / "config.json"
    if not config_path.is_file():
        return None
    try:
        payload = _read_json(config_path)
    except Exception:  # noqa: BLE001
        return None
    task = payload.get("task") if isinstance(payload, dict) else None
    if isinstance(task, dict):
        path = task.get("path")
        if isinstance(path, str) and path.strip():
            return path.strip()
    return None


def _load_task_toml(repo_root: Path, task_path: str) -> dict | None:
    toml_path = repo_root / task_path / "task.toml"
    if not toml_path.is_file():
        return None
    try:
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    return data if isinstance(data, dict) else None


def _artifact_sources(task_data: dict) -> list[str]:
    artifacts = task_data.get("artifacts")
    if not isinstance(artifacts, list):
        return []
    sources: list[str] = []
    for entry in artifacts:
        source = entry.get("source") if isinstance(entry, dict) else entry
        if isinstance(source, str) and source.strip() and _is_absolute_source(source.strip()):
            sources.append(source.strip())
    return sources


def _verifier_timeout_sec(task_data: dict) -> float:
    verifier = task_data.get("verifier")
    if isinstance(verifier, dict):
        raw = verifier.get("timeout_sec")
        if isinstance(raw, (int, float)) and raw > 0:
            return float(raw)
    return _DEFAULT_TIMEOUT_SEC


def _reward_already_present(trial_dir: Path) -> bool:
    verifier_dir = trial_dir / "verifier"
    for name in _REWARD_FILENAMES:
        path = verifier_dir / name
        if path.is_file() and path.stat().st_size > 0:
            return True
    return False


def _exception_type(trial_dir: Path) -> str | None:
    result_path = trial_dir / "result.json"
    if not result_path.is_file():
        return None
    try:
        payload = _read_json(result_path)
    except Exception:  # noqa: BLE001
        return None
    exc = payload.get("exception_info") if isinstance(payload, dict) else None
    if isinstance(exc, dict):
        exc_type = exc.get("exception_type")
        if isinstance(exc_type, str):
            return exc_type
    return None


def _read_reward_value(verifier_dir: Path) -> float | None:
    json_path = verifier_dir / "reward.json"
    if json_path.is_file() and json_path.stat().st_size > 0:
        try:
            payload = _read_json(json_path)
            reward = payload.get("reward") if isinstance(payload, dict) else None
            if isinstance(reward, (int, float)):
                return float(reward)
        except Exception:  # noqa: BLE001
            return None
    text_path = verifier_dir / "reward.txt"
    if text_path.is_file() and text_path.stat().st_size > 0:
        try:
            return float(text_path.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            return None
    return None


def _dir_has_files(path: Path) -> bool:
    if not path.is_dir():
        return False
    return any(candidate.is_file() for candidate in path.rglob("*"))


def _downloaded_artifact_dir(trial_dir: Path, source: str) -> Path:
    return trial_dir / "artifacts" / Path(source_relative_path(source))


def _stageable_sources(trial_dir: Path, sources: list[str]) -> list[tuple[str, Path]]:
    """Return (source, downloaded_dir) pairs that can be staged for host scoring."""
    stageable: list[tuple[str, Path]] = []
    for source in sources:
        downloaded = _downloaded_artifact_dir(trial_dir, source)
        if not _dir_has_files(downloaded):
            continue
        staged = Path(source)
        parent = staged.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
            probe = parent / f".matraix-host-verifier-probe-{uuid.uuid4().hex}"
            probe.write_text("", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except OSError:
            continue
        stageable.append((source, downloaded))
    return stageable


def _backup_suffix() -> str:
    return f".matraix-host-verifier-{uuid.uuid4().hex}.bak"


def _stage_sources(pairs: list[tuple[str, Path]]) -> list[tuple[Path, Path | None]]:
    """Copy downloaded artifacts onto their declared absolute sources.

    Returns a list of ``(staged_root, backup_dir_or_none)`` for restore.
    """
    staged: list[tuple[Path, Path | None]] = []
    try:
        for source, downloaded in pairs:
            staged_root = Path(source)
            backup_dir: Path | None = None
            if staged_root.exists() or staged_root.is_symlink():
                backup_dir = staged_root.with_name(staged_root.name + _backup_suffix())
                shutil.rmtree(backup_dir, ignore_errors=True)
                shutil.move(str(staged_root), str(backup_dir))
            shutil.copytree(downloaded, staged_root)
            staged.append((staged_root, backup_dir))
    except Exception:
        _restore_staged(staged)
        raise
    return staged


def _restore_staged(staged: list[tuple[Path, Path | None]]) -> None:
    for staged_root, backup_dir in reversed(staged):
        shutil.rmtree(staged_root, ignore_errors=True)
        if backup_dir is not None:
            shutil.move(str(backup_dir), str(staged_root))


def _backfill_trial_result(trial_dir: Path, reward: float) -> None:
    """Clear a stale missing-reward exception once host scoring succeeded."""
    result_path = trial_dir / "result.json"
    if not result_path.is_file():
        return
    try:
        payload = _read_json(result_path)
    except Exception:  # noqa: BLE001
        return
    if not isinstance(payload, dict):
        return
    exc = payload.get("exception_info")
    if not isinstance(exc, dict) or exc.get("exception_type") != _MISSING_REWARD_EXCEPTION:
        return
    payload["exception_info"] = None
    payload["verifier_result"] = {"rewards": {"reward": reward}}
    try:
        result_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


def maybe_run_host_verifier(
    *, repo_root: Path, trial_dir: Path, timeout_sec: float | None = None
) -> bool:
    """Run the task verifier on this host when the sandbox left no reward.

    Returns ``True`` when a host verifier run happened, ``False`` when it was
    skipped (already scored, no downloaded artifacts, source path not writable
    on this host, no test script, etc.).
    """
    if _reward_already_present(trial_dir):
        return False

    task_path = _task_path_from_trial(trial_dir)
    if not task_path:
        return False

    task_data = _load_task_toml(repo_root, task_path)
    if task_data is None:
        return False

    task_dir = repo_root / task_path
    test_sh = task_dir / "tests" / "test.sh"
    if not test_sh.is_file():
        return False

    sources = _artifact_sources(task_data)
    if not sources:
        return False

    pairs = _stageable_sources(trial_dir, sources)
    if not pairs:
        return False

    verifier_dir = trial_dir / "verifier"
    verifier_dir.mkdir(parents=True, exist_ok=True)
    effective_timeout = timeout_sec if timeout_sec is not None else _verifier_timeout_sec(task_data)

    # Serialize per absolute source so concurrent same-task trials do not race.
    locks = [_lock_for(source) for source, _ in pairs]
    for lock in locks:
        lock.acquire()
    stdout_text = ""
    try:
        staged = _stage_sources(pairs)
        try:
            env = dict(os.environ)
            env["HARBOR_VERIFIER_DIR"] = str(verifier_dir)
            try:
                completed = subprocess.run(
                    ["bash", str(test_sh)],
                    cwd=task_dir / "tests",
                    env=env,
                    timeout=effective_timeout,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                stdout_text = (completed.stdout or "") + (completed.stderr or "")
            except subprocess.TimeoutExpired as exc:
                stdout_text = (
                    f"host verifier timed out after {effective_timeout}s\n"
                    f"{exc.stdout or ''}{exc.stderr or ''}"
                )
        finally:
            _restore_staged(staged)
    finally:
        for lock in reversed(locks):
            lock.release()

    stdout_path = verifier_dir / "test-stdout.txt"
    if stdout_text.strip() and not (stdout_path.is_file() and stdout_path.stat().st_size > 0):
        try:
            stdout_path.write_text(stdout_text, encoding="utf-8")
        except OSError:
            pass

    reward = _read_reward_value(verifier_dir)
    if reward is not None and _exception_type(trial_dir) == _MISSING_REWARD_EXCEPTION:
        _backfill_trial_result(trial_dir, reward)

    return True
