#!/usr/bin/env python3
"""Run a single CocoaAgent task inside an AIO Sandbox task container."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time
from pathlib import Path

_COCOA_ROOT = os.environ.get("COCOA_ROOT", "/opt/cocoa-agent")
_PREPARED = False


def _prepare_cocoa() -> None:
    """Add cocoa-agent to sys.path and patch TaskExecutor for in-container sandbox."""
    global _PREPARED
    if _PREPARED:
        return
    _PREPARED = True

    if _COCOA_ROOT not in sys.path:
        sys.path.insert(0, _COCOA_ROOT)

    from executor import TaskExecutor

    _orig_setup = TaskExecutor.setup_environment
    _orig_cleanup = TaskExecutor.cleanup_environment

    def _patched_setup(self, task: dict, wait_time: int = 30) -> None:
        skip = self.config.get("sandbox", {}).get("skip_docker", False)
        if not skip:
            return _orig_setup(self, task, wait_time)

        import requests

        base = self.sandbox_client.base_url
        for _ in range(max(1, wait_time // 2)):
            try:
                response = requests.get(f"{base}/v1/ping", timeout=2)
                if response.status_code == 200:
                    if hasattr(self.sandbox_client, "_initialize_sdk_client"):
                        self.sandbox_client._initialize_sdk_client()
                    self.controller.clear_history()
                    if hasattr(self.controller, "reset_cost_tracking"):
                        self.controller.reset_cost_tracking()
                    return
            except Exception:
                pass
            time.sleep(2)
        raise RuntimeError(
            f"AIO Sandbox at {base} did not become ready within {wait_time}s"
        )

    def _patched_cleanup(self) -> None:
        skip = self.config.get("sandbox", {}).get("skip_docker", False)
        if skip:
            self.controller.clear_history()
        else:
            _orig_cleanup(self)

    TaskExecutor.setup_environment = _patched_setup
    TaskExecutor.cleanup_environment = _patched_cleanup

    _patch_agents_init()


def _patch_agents_init() -> None:
    """Avoid cocoa-agent eager imports that fail when optional deps are missing."""
    init_path = Path(_COCOA_ROOT) / "agents" / "__init__.py"
    safe_init = '''\
"""Agents package — minimal imports for Harbor runner."""
from .base import BaseAgent
from .cocoa_agent import CocoaAgent

__all__ = ["BaseAgent", "CocoaAgent"]
'''
    try:
        init_path.write_text(safe_init, encoding="utf-8")
    except OSError:
        pass

    if "agents" in sys.modules:
        del sys.modules["agents"]
    importlib.invalidate_caches()


def _controller_type(model: str) -> str:
    bare = model.split("/", 1)[-1].lower()
    if bare.startswith("claude"):
        return "claude"
    if bare.startswith("gemini"):
        return "gemini"
    if "qwen" in bare:
        return "qwen"
    if "deepseek" in bare:
        return "deepseek"
    return "llm"


def _api_key() -> str:
    for name in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "LLM_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise RuntimeError(
        "Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or LLM_API_KEY for persona-cocoa"
    )


def _skip_docker() -> bool:
    raw = os.environ.get("COCOA_SKIP_DOCKER", "true").strip().lower()
    return raw in ("1", "true", "yes", "on")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instruction", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--trajectory-path", required=True)
    args = parser.parse_args()

    _prepare_cocoa()

    port = int(os.environ.get("COCOA_SANDBOX_PORT", "8080"))
    base_url = os.environ.get(
        "COCOA_SANDBOX_URL", f"http://localhost:{port}"
    ).rstrip("/")

    bare_model = args.model.split("/", 1)[-1]
    config = {
        "controller": {
            "type": _controller_type(args.model),
            "args": {
                "model": bare_model,
                "api_key": _api_key(),
                "base_url": os.environ.get("LLM_BASE_URL", ""),
            },
        },
        "sandbox": {
            "client_type": "unified",
            "docker_port": port,
            "base_url": base_url,
            "max_iterations": int(os.environ.get("MAX_ITERATIONS", "30")),
            "skip_docker": _skip_docker(),
        },
    }

    from agents.cocoa_agent import CocoaAgent

    agent = CocoaAgent(config)
    task = {
        "instruction": args.instruction,
        "task_dir": "/app",
        "task_name": "harbor",
    }

    result: dict
    try:
        agent.setup_environment(task)
        result = agent.run_task(task)
    finally:
        try:
            agent.cleanup_environment()
        except Exception:
            pass

    trajectory_path = Path(args.trajectory_path)
    trajectory_path.parent.mkdir(parents=True, exist_ok=True)
    trajectory_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    if result.get("status") == "error":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
