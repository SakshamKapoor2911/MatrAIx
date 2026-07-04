#!/usr/bin/env python3
"""Diagnose use.computer macOS sandbox file upload paths (persona.yaml 502)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]
PERSONA = REPO / "persona/datasets/bench-dev-sample/persona_0012.yaml"
BASE = "https://api.use.computer"


async def main() -> int:
    key = os.environ.get("USE_COMPUTER_API_KEY", "").strip()
    if not key:
        print("FAIL: USE_COMPUTER_API_KEY not set in this shell")
        return 1
    print(f"OK: USE_COMPUTER_API_KEY present (prefix {key[:8]}...)")

    headers = {"Authorization": f"Bearer {key}"}
    async with httpx.AsyncClient(base_url=BASE, headers=headers, timeout=120.0) as client:
        print("\n[1] Create macOS sandbox...")
        resp = await client.post("/v1/sandboxes", json={"platform": "macos"})
        print(f"    status={resp.status_code}")
        if resp.status_code >= 400:
            print(resp.text[:500])
            return 1
        sb = resp.json()
        sb_id = sb.get("id") or sb.get("sandbox_id")
        print(f"    sandbox_id={sb_id}")

        prefix = f"/v1/sandboxes/{sb_id}"
        data = PERSONA.read_bytes()
        print(f"\n[2] Upload persona ({len(data)} bytes) to candidate paths...")

        paths = [
            "/app/input/persona.yaml",
            "/Users/lume/input/persona.yaml",
            "/Users/lume/workspace/persona.yaml",
            "/tmp/persona.yaml",
        ]
        results: list[tuple[str, int, str]] = []
        for path in paths:
            r = await client.put(
                f"{prefix}/files",
                params={"path": path},
                content=data,
                headers={"Content-Type": "application/octet-stream"},
            )
            snippet = r.text[:120].replace("\n", " ")
            results.append((path, r.status_code, snippet))
            print(f"    {path}: {r.status_code} {snippet}")

        print("\n[3] AsyncComputer: exec mkdir then upload /Users/lume/input/persona.yaml")
        try:
            from use_computer import AsyncComputer

            computer = await AsyncComputer.create(platform="macos")
            try:
                sb2 = computer.sandbox
                print(f"    sandbox={sb2.sandbox_id}")
                exec_result = await sb2.exec_ssh(
                    "mkdir -p /Users/lume/input && echo ok",
                    timeout=30,
                )
                print(f"    exec_ssh rc={exec_result.return_code}")
                await sb2.upload_bytes(data, "/Users/lume/input/persona.yaml")
                print("    upload_bytes /Users/lume/input/persona.yaml: OK")
            finally:
                await computer.close()
        except Exception as exc:
            print(f"    {type(exc).__name__}: {exc}")

        print("\n[4] Cleanup sandbox...")
        dr = await client.delete(prefix)
        print(f"    delete status={dr.status_code}")

        failed_app = [p for p, s, _ in results if p.startswith("/app/") and s >= 400]
        ok_lume = [p for p, s, _ in results if "/Users/lume/" in p and s < 400]
        print("\n=== Summary ===")
        if failed_app and ok_lume:
            print("LIKELY BUG: /app/... upload fails but /Users/lume/... works.")
            print("Fix: remap /app -> /Users/lume in UseComputerEnvironment._remap_macos_path")
        elif all(s >= 400 for _, s, _ in results):
            print("LIKELY: use.computer files API broken (all paths fail).")
        elif all(s < 400 for _, s, _ in results):
            print("Upload works now - earlier 502 may have been transient.")
        else:
            print("Mixed results - see per-path status above.")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
