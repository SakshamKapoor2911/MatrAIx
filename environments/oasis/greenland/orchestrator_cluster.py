#!/usr/bin/env python3
"""orchestrator_cluster.py — the controller that manages the OASIS agent dockers.

Shared-vLLM-pool topology (for "as many agents as possible"):

  - a POOL of vLLM servers (one per GPU) is started separately by vllm_pool.sh,
    listening on ports vllm-base-port .. +num-gpus-1;
  - this orchestrator builds the social graph, seeds the SHARED platform, then
    `docker run`s one THIN agent container per persona (no GPU, no private LLM);
  - each thin agent is round-robined onto a pool member via LLM_BASE_URL and
    talks to the shared platform over HTTP;
  - agents pace their steps (STEP_DELAY_S) so the social network evolves over
    wall-clock time.

It runs on the HOST (not containerized) so the -v paths it passes to agent
containers resolve on the host. Needs the docker CLI + rootless DOCKER_HOST
exported. Every `docker run` includes --pid=host and --init (mandatory on the
Greenland SDB pod; see greenland-instance-setup.sh).
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "/app")
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import requests  # noqa: E402

from environments.oasis.network import build_social_graph, NetworkConfig  # noqa: E402
from environments.oasis.persona_loader import load_personas_from_directory  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [orchestrator] %(message)s")
log = logging.getLogger("orchestrator")


def wait_for_platform(platform_url: str, timeout_s: int = 120) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if requests.get(f"{platform_url}/health", timeout=3).ok:
                log.info(f"platform healthy at {platform_url}")
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError(f"platform at {platform_url} never became healthy")


def seed_platform(platform_url: str, personas, graph) -> None:
    """Register users in index order, install follow edges, inject seed posts.

    Users are seeded with agent_id == list index, so the platform assigns
    user_id == index + 1 (DB autoincrements in insert order), matching the graph
    edges (which reference idx + 1). Each agent resolves its user_id via
    /state/{agent_id} (CLUSTER_AGENT_ID), so it never re-signs-up with a clash.
    """
    users = [{"agent_id": i, "user_name": p.user_name, "name": p.name, "bio": p.bio}
             for i, p in enumerate(personas)]
    r = requests.post(f"{platform_url}/signup/bulk", json={"users": users}, timeout=120)
    r.raise_for_status()
    log.info(f"seeded {r.json().get('registered', len(users))} users (agent_id == index)")

    if graph is not None and graph.edges:
        edges = [[e.follower_idx + 1, e.followee_idx + 1] for e in graph.edges]
        requests.post(f"{platform_url}/follow/bulk", json={"edges": edges}, timeout=120)
        log.info(f"installed {len(edges)} follow edges")
        for sp in graph.seed_posts:
            requests.post(f"{platform_url}/seed_post",
                          json={"user_id": sp.author_idx + 1, "content": sp.content}, timeout=30)
        log.info(f"injected {len(graph.seed_posts)} seed posts")


def docker_run_thin_agent(
    *,
    agent_image: str,
    agent_id: int,
    persona_path: str,
    platform_url: str,
    llm_base_url: str,
    llm_model: str,
    num_steps: int,
    step_delay_s: float,
    output_dir: str,
    network: str,
    extra_run_args: list[str],
) -> str:
    """Launch one THIN agent container (no GPU, no private vLLM)."""
    name = f"oasis-agent-{agent_id:03d}"
    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    cmd = [
        "docker", "run", "-d",
        "--name", name,
        "--init",                       # PID-1 forwards SIGTERM (else stop/rm hangs)
        "--pid=host",                   # MANDATORY on the SDB pod
        "--network", network,           # "host" on the pod (hostNetwork)
        "-e", f"AGENT_ID={agent_id}",
        "-e", f"CLUSTER_AGENT_ID={agent_id}",
        "-e", f"PERSONA_PATH={persona_path}",
        "-e", f"PLATFORM_URL={platform_url}",
        "-e", f"LLM_BASE_URL={llm_base_url}",
        "-e", f"LLM_MODEL={llm_model}",
        "-e", f"NUM_STEPS={num_steps}",
        "-e", f"STEP_DELAY_S={step_delay_s}",
        "-e", f"OUTPUT_PATH=/app/output/trajectory_{agent_id:03d}.json",
        "-v", f"{output_dir}:/app/output",
        "--entrypoint", "/app/environments/oasis/greenland/agent_entrypoint_thin.sh",
        *extra_run_args,
        agent_image,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        log.error(f"failed to launch {name}: {res.stderr.strip()}")
        raise RuntimeError(res.stderr.strip())
    return name


def wait_for_containers(names: list[str], poll_s: int = 10) -> dict[str, int]:
    """Block until all agent containers exit; return name -> exit code."""
    remaining = set(names)
    exit_codes: dict[str, int] = {}
    while remaining:
        time.sleep(poll_s)
        for name in list(remaining):
            res = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}} {{.State.ExitCode}}", name],
                capture_output=True, text=True,
            )
            out = res.stdout.strip()
            if not out:
                continue
            running, code = (out.split() + ["?"])[:2]
            if running == "false":
                exit_codes[name] = int(code) if code.isdigit() else -1
                remaining.discard(name)
                log.info(f"{name} finished (exit {exit_codes[name]}); {len(remaining)} remaining")
    return exit_codes


def main() -> int:
    ap = argparse.ArgumentParser(description="OASIS multi-agent Docker orchestrator (shared vLLM pool)")
    ap.add_argument("--personas-dir", default="personas/Jun20_1k_persona_description",
                    help="dir the orchestrator reads personas from (HOST path) to build the graph")
    ap.add_argument("--container-personas-dir", default="personas/Jun20_1k_persona_description",
                    help="dir the agent IMAGE has personas at (repo-relative; COPYd to /app)")
    ap.add_argument("--num-agents", type=int, default=64)
    ap.add_argument("--num-steps", type=int, default=30)
    ap.add_argument("--step-delay-s", type=float, default=0.0,
                    help="seconds an agent sleeps between steps (paces the sim over wall-clock)")
    ap.add_argument("--agent-image", default="oasis-agent:latest")
    ap.add_argument("--platform-url", default="http://127.0.0.1:8000")
    ap.add_argument("--llm-model", default="Qwen/Qwen3-8B")
    # Shared vLLM pool on ports vllm-base-port .. +num-gpus-1 (started by vllm_pool.sh)
    ap.add_argument("--num-gpus", type=int, default=8)
    ap.add_argument("--vllm-base-port", type=int, default=8200)
    ap.add_argument("--launch-stagger-s", type=float, default=0.5,
                    help="delay between launching successive agent containers")
    ap.add_argument("--network", default="host", help="docker network (host on the SDB pod)")
    ap.add_argument("--output-dir", default="/app/output")
    ap.add_argument("--random-seed", type=int, default=42)
    ap.add_argument("--extra-run-arg", action="append", default=[],
                    help="extra arg passed verbatim to each `docker run` (repeatable)")
    args = ap.parse_args()

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    log.info(f"loading up to {args.num_agents} personas from {args.personas_dir}")
    personas = load_personas_from_directory(args.personas_dir, max_agents=args.num_agents)
    persona_files = (sorted(Path(args.personas_dir).glob("*.yaml"))
                     or sorted(Path(args.personas_dir).glob("*.yml")))[:len(personas)]
    log.info(f"loaded {len(personas)} personas ({len(persona_files)} files)")

    graph = build_social_graph(personas, NetworkConfig(random_seed=args.random_seed))

    wait_for_platform(args.platform_url)
    seed_platform(args.platform_url, personas, graph)

    base = args.platform_url.rsplit(":", 1)[0]  # e.g. http://127.0.0.1
    log.info(f"launching {len(personas)} thin agents across {args.num_gpus} vLLM pool members "
             f"(ports {args.vllm_base_port}..{args.vllm_base_port + args.num_gpus - 1}), "
             f"step_delay={args.step_delay_s}s")
    names: list[str] = []
    for i, p in enumerate(personas):
        pool_port = args.vllm_base_port + (i % args.num_gpus)   # round-robin the pool
        llm_base_url = f"{base}:{pool_port}/v1"
        persona_file = f"{args.container_personas_dir}/{persona_files[i].name}"
        names.append(docker_run_thin_agent(
            agent_image=args.agent_image,
            agent_id=i,
            persona_path=persona_file,
            platform_url=args.platform_url,
            llm_base_url=llm_base_url,
            llm_model=args.llm_model,
            num_steps=args.num_steps,
            step_delay_s=args.step_delay_s,
            output_dir=args.output_dir,
            network=args.network,
            extra_run_args=args.extra_run_arg,
        ))
        if (i + 1) % 16 == 0:
            log.info(f"  launched {i + 1}/{len(personas)} agents")
        if args.launch_stagger_s > 0:
            time.sleep(args.launch_stagger_s)

    log.info(f"launched {len(names)} agent containers; waiting for completion...")
    exit_codes = wait_for_containers(names)

    stats, traces = {}, []
    try:
        stats = requests.get(f"{args.platform_url}/stats", timeout=30).json()
        traces = requests.get(f"{args.platform_url}/traces", timeout=60).json()
    except requests.RequestException as e:
        log.warning(f"could not pull final platform state: {e}")

    summary = {
        "num_agents": len(names),
        "num_steps": args.num_steps,
        "step_delay_s": args.step_delay_s,
        "llm_model": args.llm_model,
        "num_gpus": args.num_gpus,
        "topology": "shared_vllm_pool",
        "agent_exit_codes": exit_codes,
        "agents_succeeded": sum(1 for c in exit_codes.values() if c == 0),
        "platform_stats": stats,
        "trace_count": len(traces) if isinstance(traces, list) else None,
    }
    out_path = Path(args.output_dir) / "cluster_summary.json"
    out_path.write_text(json.dumps(summary, indent=2))
    log.info(f"run complete. summary -> {out_path}")
    log.info(json.dumps(summary, indent=2))
    return 0 if summary["agents_succeeded"] == len(names) else 1


if __name__ == "__main__":
    raise SystemExit(main())
