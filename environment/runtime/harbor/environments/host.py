"""Host-native Harbor environment for native survey/chat trial profiles."""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from harbor.constants import MAIN_SERVICE_NAME
from harbor.environments.base import BaseEnvironment, ExecResult
from harbor.environments.capabilities import EnvironmentCapabilities
from harbor.models.environment_type import EnvironmentType
from harbor.models.task.config import EnvironmentConfig
from harbor.models.trial.paths import EnvironmentPaths, TrialPaths

_CONTAINER_PATH_PATTERN = re.compile(
    r"/(?:app|tests)(?:/[^\s'\"`;]+)?|/logs/verifier(?:/[^\s'\"`;]+)?"
)


class HostEnvironment(BaseEnvironment):
    """Run agent + verifier on the host without building the task main image."""

    _sidecar_api_marker = ".sidecar_api_url"

    def __init__(
        self,
        environment_dir: Path,
        environment_name: str,
        session_id: str,
        trial_paths: TrialPaths,
        task_env_config: EnvironmentConfig,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(
            environment_dir=environment_dir,
            environment_name=environment_name,
            session_id=session_id,
            trial_paths=trial_paths,
            task_env_config=task_env_config,
            **kwargs,
        )
        self._workspace_root = self.trial_paths.trial_dir / "host_workspace"
        self._tests_root = self.trial_paths.trial_dir / "host_tests"
        self._compose_project = self._compose_project_name()
        self._sidecar_services: list[str] = []
        self._sidecar_compose_path: Path | None = None

    @staticmethod
    def type() -> EnvironmentType:
        return EnvironmentType.HOST

    @property
    def capabilities(self) -> EnvironmentCapabilities:
        return EnvironmentCapabilities(mounted=True)

    def _validate_definition(self) -> None:
        return None

    def _compose_project_name(self) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", self.session_id.lower()).strip("-")
        return slug or "harbor-host-trial"

    def _env_paths(self) -> EnvironmentPaths:
        return EnvironmentPaths.for_os(self.os)

    def resolve_container_path(self, container_path: str) -> Path:
        path = PurePosixPath(container_path)
        parts = [part for part in path.parts if part != "/"]
        if not parts:
            raise ValueError("container path must not be empty")
        if parts[0] == "app":
            host_path = self.trial_paths.host_artifact_path(
                MAIN_SERVICE_NAME, "/" + "/".join(parts)
            )
        elif len(parts) >= 2 and parts[0] == "logs" and parts[1] == "verifier":
            rel = Path(*parts[2:]) if len(parts) > 2 else Path(".")
            host_path = self.trial_paths.verifier_dir / rel
        elif parts[0] == "tests":
            rel = Path(*parts[1:]) if len(parts) > 1 else Path(".")
            host_path = self._tests_root / rel
        else:
            raise ValueError("unsupported host container path: {}".format(container_path))
        return host_path.resolve()

    def _rewrite_command_paths(self, command: str) -> str:
        rewritten = command
        for match in _CONTAINER_PATH_PATTERN.findall(rewritten):
            host_path = self.resolve_container_path(match.rstrip("/"))
            if match.endswith("/"):
                host_path = host_path / ""
            rewritten = rewritten.replace(match, str(host_path), 1)
        return rewritten

    @staticmethod
    def _normalize_shell_invocation(command: str) -> str:
        """Run verifier scripts via bash; direct execution is brittle on host."""
        return re.sub(
            r"\(\s*('(?:[^']|\\')*\.sh'|\"(?:[^\"]|\\\")*\.sh\")\s*\)",
            r"bash \1",
            command,
        )

    def _ensure_redirect_targets(self, command: str) -> None:
        for match in re.finditer(r">\s*('([^']+)'|\"([^\"]+)\")", command):
            target = match.group(2) or match.group(3)
            if not target:
                continue
            Path(target).parent.mkdir(parents=True, exist_ok=True)

    def _discover_sidecar_services(self) -> list[str]:
        compose_path = self.environment_dir / "docker-compose.yaml"
        if not compose_path.is_file():
            return []
        payload = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return []
        services = payload.get("services")
        if not isinstance(services, dict):
            return []
        return [name for name in services if name != "main"]

    async def _run_command(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout_sec: int | None = None,
    ) -> ExecResult:
        merged = os.environ.copy()
        if env:
            merged.update(env)
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(cwd) if cwd else None,
            env=merged,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            if timeout_sec:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_sec,
                )
            else:
                stdout_bytes, stderr_bytes = await process.communicate()
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            raise RuntimeError("host command timed out after {}s".format(timeout_sec)) from None
        return ExecResult(
            stdout=stdout_bytes.decode(errors="replace") if stdout_bytes else None,
            stderr=stderr_bytes.decode(errors="replace") if stderr_bytes else None,
            return_code=process.returncode or 0,
        )

    def _sidecar_build_context(self, service_name: str) -> str:
        compose_path = self.environment_dir / "docker-compose.yaml"
        payload = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return "."
        services = payload.get("services")
        if not isinstance(services, dict):
            return "."
        service = services.get(service_name)
        if not isinstance(service, dict):
            return "."
        build = service.get("build")
        if isinstance(build, dict):
            return str(build.get("context") or ".")
        if isinstance(build, str):
            return build
        return "."

    async def _start_sidecars(self, force_build: bool) -> None:
        services = self._discover_sidecar_services()
        if not services:
            return
        self._sidecar_services = services
        service_name = services[0]
        from persona_eval.inprocess.chatbot_sidecar_compose import (
            write_standalone_sidecar_compose,
        )

        compose_dir = self.trial_paths.trial_dir / "host_compose"
        compose_path = write_standalone_sidecar_compose(
            compose_dir=self.environment_dir,
            service_name=service_name,
            build_context=self._sidecar_build_context(service_name),
            port_mapping="127.0.0.1::8000",
            output_dir=compose_dir,
        )
        self._sidecar_compose_path = compose_path
        command = [
            "docker",
            "compose",
            "--project-name",
            self._compose_project,
            "--project-directory",
            str(self.environment_dir),
            "-f",
            str(compose_path),
            "up",
            "-d",
            service_name,
        ]
        if force_build:
            command.append("--build")
        result = await self._run_command(command, timeout_sec=900)
        if result.return_code != 0:
            raise RuntimeError(
                "failed to start chat sidecar: {}".format(result.stderr or result.stdout)
            )
        port_result = await self._run_command(
            [
                "docker",
                "compose",
                "--project-name",
                self._compose_project,
                "--project-directory",
                str(self.environment_dir),
                "-f",
                str(compose_path),
                "port",
                service_name,
                "8000",
            ],
            timeout_sec=30,
        )
        if port_result.return_code != 0:
            raise RuntimeError(
                "failed to resolve chat sidecar port: {}".format(
                    port_result.stderr or port_result.stdout
                )
            )
        port_line = (port_result.stdout or "").strip().splitlines()[-1]
        host, _, port = port_line.rpartition(":")
        api_url = "http://{}:{}".format(host or "127.0.0.1", port)
        await self._wait_for_sidecar_port(host or "127.0.0.1", int(port))
        marker = self.trial_paths.trial_dir / self._sidecar_api_marker
        marker.write_text(api_url + "\n", encoding="utf-8")

    async def _wait_for_sidecar_port(
        self,
        host: str,
        port: int,
        *,
        timeout_sec: float = 30.0,
    ) -> None:
        deadline = asyncio.get_running_loop().time() + timeout_sec
        while asyncio.get_running_loop().time() < deadline:
            try:
                reader, writer = await asyncio.open_connection(host, port)
                writer.close()
                await writer.wait_closed()
                return
            except OSError:
                await asyncio.sleep(0.5)
        raise RuntimeError(
            "chat sidecar did not become reachable at {}:{} within {}s".format(
                host,
                port,
                int(timeout_sec),
            )
        )

    async def start(self, force_build: bool) -> None:
        self._workspace_root.mkdir(parents=True, exist_ok=True)
        self._tests_root.mkdir(parents=True, exist_ok=True)
        output_dir = self.resolve_container_path("/app/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        self.trial_paths.verifier_dir.mkdir(parents=True, exist_ok=True)
        await self._start_sidecars(force_build)

    async def stop(self, delete: bool) -> None:
        if not self._sidecar_services:
            return
        compose_path = self._sidecar_compose_path
        command = [
            "docker",
            "compose",
            "--project-name",
            self._compose_project,
            "--project-directory",
            str(self.environment_dir),
        ]
        if compose_path is not None:
            command.extend(["-f", str(compose_path)])
        command.extend(["down", "--remove-orphans"])
        if delete:
            command.extend(["--volumes", "--rmi", "local"])
        await self._run_command(command, timeout_sec=120)
        marker = self.trial_paths.trial_dir / self._sidecar_api_marker
        marker.unlink(missing_ok=True)

    async def upload_file(self, source_path: Path | str, target_path: str) -> None:
        source = Path(source_path)
        destination = self.resolve_container_path(target_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    async def upload_dir(self, source_dir: Path | str, target_dir: str) -> None:
        source = Path(source_dir)
        destination = self.resolve_container_path(target_dir.rstrip("/") + "/.")
        if destination.name == ".":
            destination = destination.parent
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)

    async def download_file(self, source_path: str, target_path: Path | str) -> None:
        source = self.resolve_container_path(source_path)
        destination = Path(target_path).resolve()
        if source.resolve() == destination:
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    async def download_dir(self, source_dir: str, target_dir: Path | str) -> None:
        source = self.resolve_container_path(source_dir.rstrip("/") + "/.")
        if source.name == ".":
            source = source.parent
        source = source.resolve()
        destination = Path(target_dir).resolve()
        # Host uploads land directly under the artifact mount; collection must not
        # rmtree/copytree the same path (that wipes agent output before verify).
        if source == destination:
            return
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)

    async def exec(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout_sec: int | None = None,
        user: str | int | None = None,
    ) -> ExecResult:
        del user
        self._workspace_root.mkdir(parents=True, exist_ok=True)
        self._tests_root.mkdir(parents=True, exist_ok=True)
        self.trial_paths.verifier_dir.mkdir(parents=True, exist_ok=True)
        output_dir = self.resolve_container_path("/app/output")
        output_dir.mkdir(parents=True, exist_ok=True)

        rewritten = self._normalize_shell_invocation(self._rewrite_command_paths(command))
        self._ensure_redirect_targets(rewritten)
        workdir = self._workspace_root.resolve()
        if cwd:
            workdir = self.resolve_container_path(cwd)
        merged_env = dict(env or {})
        merged_env["MATRIX_OUTPUT_DIR"] = str(output_dir)
        merged_env["PERSONABENCH_OUTPUT_DIR"] = str(output_dir)
        merged_env["HARBOR_VERIFIER_DIR"] = str(self.trial_paths.verifier_dir.resolve())
        merged_env["HARBOR_TESTS_DIR"] = str(self._tests_root.resolve())
        return await self._run_command(
            ["bash", "-c", rewritten],
            cwd=workdir,
            env=merged_env,
            timeout_sec=timeout_sec,
        )
