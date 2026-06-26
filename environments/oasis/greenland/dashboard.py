#!/usr/bin/env python3
"""dashboard.py — live web dashboard for the OASIS multi-agent Docker sim.

Runs ON THE HOST (conda env), serves a single auto-refreshing page that shows:
  - LEFT: docker lifecycle — every agent container spinning up -> active ->
    exited, plus the vLLM pool + platform, and per-GPU memory bars;
  - RIGHT: the live social world — posts / follows / likes / comments / reposts
    counters and recent activity, polled from the platform.

It shells out to `docker ps`, `nvidia-smi`, and hits the platform HTTP API. View
it from your laptop over the SSH tunnel:
    ssh -p 1057 -L 8500:127.0.0.1:8500 greenland-user@localhost   (or add -L to the tunnel)
    open http://127.0.0.1:8500

Usage (host, rootless docker env exported):
    python environments/oasis/greenland/dashboard.py --port 8500 --platform-url http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from typing import Any

import requests
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

PLATFORM_URL = os.environ.get("PLATFORM_URL", "http://127.0.0.1:8000")
START_TIME = time.time()


def _docker(*args: str) -> str:
    env = {**os.environ}
    env.setdefault("XDG_RUNTIME_DIR", os.path.expanduser("~/.docker/run"))
    env.setdefault("DOCKER_HOST", f"unix://{env['XDG_RUNTIME_DIR']}/docker.sock")
    try:
        return subprocess.run(["docker", *args], capture_output=True, text=True, env=env, timeout=15).stdout
    except Exception:
        return ""


def container_state() -> dict[str, Any]:
    """Classify all oasis containers into lifecycle buckets."""
    out = _docker("ps", "-a", "--format", "{{.Names}}\t{{.Status}}\t{{.State}}")
    agents, vllm, platform = [], [], []
    counts = {"created": 0, "running": 0, "exited": 0}
    for line in out.strip().splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        name, status, state = parts[0], parts[1], parts[2]
        row = {"name": name, "status": status, "state": state}
        if name.startswith("oasis-agent-"):
            agents.append(row)
            counts[state] = counts.get(state, 0) + 1
        elif name.startswith("oasis-vllm-"):
            vllm.append(row)
        elif name == "oasis-platform":
            platform.append(row)
    agents.sort(key=lambda r: r["name"])
    return {"agents": agents, "vllm": vllm, "platform": platform, "agent_counts": counts}


def gpu_state() -> list[dict[str, Any]]:
    out = _docker_nvidia()
    gpus = []
    for line in out.strip().splitlines():
        p = [x.strip() for x in line.split(",")]
        if len(p) >= 3:
            try:
                idx, used, total = int(p[0]), int(p[1]), int(p[2])
                gpus.append({"index": idx, "used_mib": used, "total_mib": total,
                             "pct": round(100 * used / total) if total else 0})
            except ValueError:
                pass
    return gpus


def _docker_nvidia() -> str:
    try:
        return subprocess.run(
            ["nvidia-smi", "--query-gpu=index,memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return ""


def platform_state() -> dict[str, Any]:
    try:
        stats = requests.get(f"{PLATFORM_URL}/stats", timeout=4).json()
    except requests.RequestException:
        stats = {}
    try:
        traces = requests.get(f"{PLATFORM_URL}/traces?limit=12", timeout=4).json()
        recent = [{"user_id": t.get("user_id"), "action": t.get("action_type") or t.get("action")}
                  for t in (traces if isinstance(traces, list) else [])][:12]
    except requests.RequestException:
        recent = []
    return {"stats": stats, "recent": recent}


app = FastAPI(title="OASIS Sim Dashboard")


@app.get("/api/state")
def api_state() -> JSONResponse:
    cs = container_state()
    return JSONResponse({
        "elapsed_s": int(time.time() - START_TIME),
        "containers": cs,
        "gpus": gpu_state(),
        "platform": platform_state(),
    })


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return HTML_PAGE


HTML_PAGE = """<!doctype html><html><head><meta charset=utf-8>
<title>OASIS Multi-Agent Sim</title>
<style>
 body{font-family:-apple-system,Segoe UI,Roboto,monospace;margin:0;background:#0b0e14;color:#d7dce5}
 header{padding:12px 18px;background:#11161f;border-bottom:1px solid #1f2733;display:flex;gap:24px;align-items:center}
 header h1{font-size:16px;margin:0;color:#8ab4ff}
 .pill{background:#1a2230;border-radius:12px;padding:3px 10px;font-size:12px}
 .wrap{display:flex;gap:14px;padding:14px}
 .col{flex:1;background:#11161f;border:1px solid #1f2733;border-radius:10px;padding:12px}
 h2{font-size:13px;color:#9aa7bd;margin:0 0 8px;text-transform:uppercase;letter-spacing:.5px}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(86px,1fr));gap:5px}
 .cell{border-radius:6px;padding:6px 4px;font-size:10px;text-align:center;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
 .created{background:#3a2f12;color:#e8c97a}
 .running{background:#123a1d;color:#7ee29b}
 .exited{background:#2a2f3a;color:#8b97ab}
 .bar{height:14px;background:#1a2230;border-radius:7px;overflow:hidden;margin:3px 0}
 .bar>div{height:100%;background:linear-gradient(90deg,#3b82f6,#22c55e)}
 .stat{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1a2230;font-size:13px}
 .stat b{color:#7ee29b;font-size:15px}
 .big{font-size:26px;color:#8ab4ff}
 .svc{font-size:12px;padding:3px 0}
 .recent div{font-size:11px;color:#9aa7bd;padding:1px 0}
 small{color:#5b6678}
</style></head><body>
<header>
 <h1>🌐 OASIS Multi-Agent Social Simulation</h1>
 <span class=pill id=elapsed>elapsed 0s</span>
 <span class=pill id=agentsum>agents –</span>
 <span class=pill id=model>shared vLLM pool</span>
</header>
<div class=wrap>
 <div class=col>
  <h2>Docker · agents spinning up → active</h2>
  <div id=svcs></div>
  <div class=grid id=agents></div>
  <h2 style="margin-top:14px">GPU memory (8× A100-40GB)</h2>
  <div id=gpus></div>
 </div>
 <div class=col>
  <h2>Social world (live)</h2>
  <div style="display:flex;gap:18px;margin-bottom:8px">
   <div><div class=big id=posts>0</div><small>posts</small></div>
   <div><div class=big id=follows>0</div><small>follows</small></div>
   <div><div class=big id=likes>0</div><small>likes</small></div>
   <div><div class=big id=traces>0</div><small>actions</small></div>
  </div>
  <div id=stats></div>
  <h2 style="margin-top:14px">Recent activity</h2>
  <div class=recent id=recent></div>
 </div>
</div>
<script>
async function tick(){
 try{
  const s=await (await fetch('/api/state')).json();
  document.getElementById('elapsed').textContent='elapsed '+Math.floor(s.elapsed_s/60)+'m '+(s.elapsed_s%60)+'s';
  const c=s.containers.agent_counts||{};
  document.getElementById('agentsum').textContent=
    `agents: ${c.running||0} active · ${c.created||0} starting · ${c.exited||0} done`;
  // services
  const svc=[...(s.containers.platform||[]),...(s.containers.vllm||[])]
    .map(r=>`<div class=svc>${r.state==='running'?'🟢':'⚪'} ${r.name} <small>${r.status}</small></div>`).join('');
  document.getElementById('svcs').innerHTML=svc||'<small>no services yet</small>';
  // agents grid
  document.getElementById('agents').innerHTML=(s.containers.agents||[])
    .map(a=>`<div class="cell ${a.state}" title="${a.name} ${a.status}">${a.name.replace('oasis-agent-','#')}</div>`).join('')
    || '<small>waiting for agents…</small>';
  // gpus
  document.getElementById('gpus').innerHTML=(s.gpus||[])
    .map(g=>`<div>GPU ${g.index} <small>${g.used_mib}/${g.total_mib} MiB</small><div class=bar><div style="width:${g.pct}%"></div></div></div>`).join('');
  // platform
  const st=s.platform.stats||{};
  document.getElementById('posts').textContent=st.post||0;
  document.getElementById('follows').textContent=st.follow||0;
  document.getElementById('likes').textContent=st.like||0;
  document.getElementById('traces').textContent=st.trace||0;
  document.getElementById('stats').innerHTML=
    ['user','post','comment','repost','like','follow','rec']
    .filter(k=>k in st).map(k=>`<div class=stat><span>${k}</span><b>${st[k]}</b></div>`).join('');
  document.getElementById('recent').innerHTML=(s.platform.recent||[])
    .map(r=>`<div>user ${r.user_id} → ${r.action}</div>`).join('')||'<small>no activity yet</small>';
 }catch(e){}
 setTimeout(tick,2000);
}
tick();
</script></body></html>"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8500)
    ap.add_argument("--platform-url", default=PLATFORM_URL)
    args = ap.parse_args()
    PLATFORM_URL = args.platform_url
    uvicorn.run(app, host="0.0.0.0", port=args.port)
