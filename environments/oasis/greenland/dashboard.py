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
DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/MatrAIx/environments/oasis/output/simulation.db"))
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
    posts = _posts_from_http() or _posts_from_db()
    return {"stats": stats, "recent": recent, "posts": posts}


def _posts_from_http() -> list[dict[str, Any]]:
    """Preferred path: the platform's /posts endpoint (if it has it)."""
    try:
        r = requests.get(f"{PLATFORM_URL}/posts?limit=40", timeout=5)
        data = r.json()
        if r.ok and isinstance(data, list):
            return data
    except (requests.RequestException, ValueError):
        pass
    return []


def _posts_from_db() -> list[dict[str, Any]]:
    """Fallback: read posts straight from the platform's SQLite file (read-only).

    Lets the dashboard show post text against an ALREADY-RUNNING platform that
    predates the /posts endpoint, without restarting it (which would wipe state).
    """
    if not DB_PATH or not os.path.exists(DB_PATH):
        return []
    import sqlite3
    try:
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=3)
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT p.post_id, p.user_id, p.content, p.original_post_id, "
            "p.num_likes, p.num_comments, p.num_shares, u.name, u.user_name "
            "FROM post p LEFT JOIN user u ON u.user_id = p.user_id "
            "ORDER BY p.created_at DESC LIMIT 40"
        ).fetchall()
        con.close()
        return [{
            "post_id": r["post_id"], "user_id": r["user_id"],
            "author": r["name"] or r["user_name"] or f"user{r['user_id']}",
            "content": r["content"], "is_repost": r["original_post_id"] is not None,
            "num_likes": r["num_likes"] or 0, "num_comments": r["num_comments"] or 0,
            "num_shares": r["num_shares"] or 0,
        } for r in rows]
    except Exception:
        return []


def _graph_from_http() -> dict[str, Any] | None:
    """Build the agent graph from the platform's live /threads HTTP endpoint.

    HTTP-first (same reason as threads_state): the running platform is the
    source of truth. A restarted platform can hold its DB on a deleted inode,
    leaving the on-disk file stale — so reading the file shows the wrong graph.
    Nodes = post authors + commenters; edges = commenter -> post-author (the
    real agent-to-agent interaction the 3D viewer animates).
    """
    try:
        r = requests.get(f"{PLATFORM_URL}/threads?limit=200", timeout=6)
        if not r.ok:
            return None
        threads = r.json().get("threads", [])
    except (requests.RequestException, ValueError):
        return None
    names: dict[int, str] = {}
    posts_per_user: dict[int, int] = {}
    edge_w: dict[tuple, dict] = {}
    for t in threads:
        au = t.get("user_id")
        if au is None:
            continue
        names[au] = t.get("author", f"user{au}")
        posts_per_user[au] = posts_per_user.get(au, 0) + 1
        for c in t.get("comments", []):
            cu = c.get("user_id")
            if cu is None:
                continue
            names[cu] = c.get("author", f"user{cu}")
            if cu != au:
                k = (cu, au, "create_comment")
                e = edge_w.setdefault(k, {"source": cu, "target": au,
                                          "action": "create_comment", "weight": 0})
                e["weight"] += 1
    if not names:
        return None
    nodes = [{"user_id": uid, "name": nm, "posts": posts_per_user.get(uid, 0),
              "followers": 0} for uid, nm in names.items()]
    return {"nodes": nodes, "edges": list(edge_w.values()), "recent_edges": [], "source": "http"}


def graph_state() -> dict[str, Any]:
    """Agent-interaction graph. HTTP-first (live platform), SQLite fallback.

    Nodes = agents (persona name + post count); edges = actor -> target-author
    interactions. This is what the 3D viewer animates.
    """
    http = _graph_from_http()
    if http is not None:
        return http
    if not DB_PATH or not os.path.exists(DB_PATH):
        return {"nodes": [], "edges": [], "container_by_user": {}}
    import sqlite3
    try:
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=3)
        con.row_factory = sqlite3.Row

        users = con.execute(
            "SELECT user_id, name, user_name, num_followers, num_followings FROM user"
        ).fetchall()
        post_author = {r["post_id"]: r["user_id"]
                       for r in con.execute("SELECT post_id, user_id FROM post").fetchall()}
        posts_per_user: dict[int, int] = {}
        for r in con.execute("SELECT user_id, COUNT(*) c FROM post GROUP BY user_id").fetchall():
            posts_per_user[r["user_id"]] = r["c"]

        # Aggregate interaction edges from traces (most recent first, capped).
        edge_w: dict[tuple, dict] = {}
        recent_edges: list[dict] = []
        traces = con.execute(
            "SELECT user_id, action, info, created_at FROM trace "
            "WHERE action IN ('like_post','create_comment','repost','quote_post','follow') "
            "ORDER BY trace_id DESC LIMIT 4000"
        ).fetchall()
        for t in traces:
            actor = t["user_id"]
            try:
                info = json.loads(t["info"] or "{}")
            except Exception:
                info = {}
            params = info.get("params", {}) if isinstance(info, dict) else {}
            target = None
            if t["action"] == "follow":
                target = params.get("target_id") or params.get("user_id")
            else:
                pid = params.get("post_id")
                if pid is not None:
                    target = post_author.get(pid)
            if target is None or target == actor:
                continue
            key = (actor, target, t["action"])
            e = edge_w.setdefault(key, {"source": actor, "target": target,
                                        "action": t["action"], "weight": 0})
            e["weight"] += 1
            if len(recent_edges) < 60:
                recent_edges.append({"source": actor, "target": target,
                                     "action": t["action"], "at": t["created_at"]})
        con.close()

        nodes = [{
            "user_id": u["user_id"],
            "name": u["name"] or u["user_name"] or f"user{u['user_id']}",
            "posts": posts_per_user.get(u["user_id"], 0),
            "followers": u["num_followers"] or 0,
        } for u in users]
        return {
            "nodes": nodes,
            "edges": list(edge_w.values()),
            "recent_edges": recent_edges,
        }
    except Exception as exc:  # noqa: BLE001
        return {"nodes": [], "edges": [], "error": str(exc)}


def threads_state(limit: int = 40) -> dict[str, Any]:
    """Return the social feed as threaded conversations: each recent post with
    its author, engagement, quote/repost link, and its comments (each with the
    commenter's persona name). This is the 'social media platform' view.

    Prefer the platform's /threads HTTP endpoint (ALWAYS the live in-process
    state) over reading the SQLite file. Reading the file is fragile: the
    platform can hold the DB open on a deleted inode after a restart, so the
    on-disk file goes stale while the API stays correct. HTTP-first avoids that
    whole class of bug; the DB read is only a last-resort fallback.
    """
    try:
        r = requests.get(f"{PLATFORM_URL}/threads?limit={limit}", timeout=5)
        data = r.json()
        if r.ok and isinstance(data, dict) and "threads" in data:
            return data
    except (requests.RequestException, ValueError):
        pass
    if not DB_PATH or not os.path.exists(DB_PATH):
        return {"threads": []}
    import sqlite3
    try:
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=3)
        con.row_factory = sqlite3.Row
        names = {r["user_id"]: (r["name"] or r["user_name"] or f"user{r['user_id']}")
                 for r in con.execute("SELECT user_id, name, user_name FROM user").fetchall()}
        posts = con.execute(
            "SELECT post_id, user_id, content, original_post_id, quote_content, "
            "num_likes, num_comments, num_shares, created_at "
            "FROM post ORDER BY post_id DESC LIMIT ?", (limit,)
        ).fetchall()
        # comments for just these posts
        pids = [p["post_id"] for p in posts]
        comments_by_post: dict[int, list] = {}
        if pids:
            q = ("SELECT comment_id, post_id, user_id, content, num_likes, created_at "
                 f"FROM comment WHERE post_id IN ({','.join('?'*len(pids))}) ORDER BY comment_id ASC")
            for c in con.execute(q, pids).fetchall():
                comments_by_post.setdefault(c["post_id"], []).append({
                    "comment_id": c["comment_id"],
                    "user_id": c["user_id"],
                    "author": names.get(c["user_id"], f"user{c['user_id']}"),
                    "content": c["content"],
                    "num_likes": c["num_likes"] or 0,
                })
        con.close()
        threads = []
        for p in posts:
            threads.append({
                "post_id": p["post_id"],
                "user_id": p["user_id"],
                "author": names.get(p["user_id"], f"user{p['user_id']}"),
                "content": p["content"],
                "is_repost": p["original_post_id"] is not None,
                "quote": p["quote_content"],
                "num_likes": p["num_likes"] or 0,
                "num_comments": p["num_comments"] or 0,
                "num_shares": p["num_shares"] or 0,
                "comments": comments_by_post.get(p["post_id"], []),
            })
        return {"threads": threads}
    except Exception as exc:  # noqa: BLE001
        return {"threads": [], "error": str(exc)}


app = FastAPI(title="MatrAIx Agent Simulation")


@app.get("/api/state")
def api_state() -> JSONResponse:
    return JSONResponse({
        "elapsed_s": int(time.time() - START_TIME),
        "containers": container_state(),
        "gpus": gpu_state(),
        "platform": platform_state(),
    })


@app.get("/api/graph")
def api_graph() -> JSONResponse:
    return JSONResponse(graph_state())


@app.get("/api/threads")
def api_threads() -> JSONResponse:
    return JSONResponse(threads_state())


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return GRAPH_PAGE


@app.get("/feed", response_class=HTMLResponse)
def feed() -> str:
    return FEED_PAGE


# =====================================================================
#  /  — 3D knowledge graph (MatrAIx agent interaction network)
# =====================================================================
GRAPH_PAGE = """<!doctype html><html><head><meta charset=utf-8>
<title>MatrAIx — Agent Network</title>
<!-- 3d-force-graph bundles its own three.js; do NOT load three separately. -->
<script src="https://unpkg.com/3d-force-graph"></script>
<style>
 html,body{margin:0;height:100%;background:#04060c;color:#e6ebf5;font-family:-apple-system,Segoe UI,Roboto,sans-serif;overflow:hidden}
 #bar{position:fixed;top:0;left:0;right:0;height:46px;background:linear-gradient(90deg,#0a1424,#0a0f1c);border-bottom:1px solid #1b2740;display:flex;gap:14px;align-items:center;padding:0 18px;z-index:20}
 #bar h1{font-size:15px;margin:0;font-weight:700;letter-spacing:.3px;background:linear-gradient(90deg,#8ab4ff,#a6f0d0);-webkit-background-clip:text;background-clip:text;color:transparent}
 .pill{background:#12203a;border:1px solid #1b2740;border-radius:20px;padding:4px 11px;font-size:12px;color:#c3cee2}
 a.pill{text-decoration:none;color:#8ab4ff}
 #graph{position:fixed;top:46px;left:0;right:0;bottom:0}
 #panel{position:fixed;top:58px;right:14px;width:320px;max-height:calc(100vh-76px);overflow:auto;background:#0a1220ee;border:1px solid #1b2740;border-radius:12px;padding:14px;font-size:12px;z-index:15;display:none;backdrop-filter:blur(6px)}
 #panel h3{margin:0 0 4px;font-size:15px;color:#a6f0d0}
 #panel .sub{color:#5f6f8c;font-size:11px;margin-bottom:8px}
 #panel .post{background:#0e1830;border:1px solid #1c2c4a;border-radius:9px;padding:8px 10px;margin:7px 0}
 #panel .cm{margin:5px 0 0 10px;padding:4px 8px;border-left:2px solid #22c55e66;color:#a7c8b6;font-size:11.5px}
 #close{float:right;color:#5f6f8c;cursor:pointer;font-size:14px}
 #tip{position:fixed;bottom:12px;left:14px;font-size:11px;color:#5f6f8c;background:#0a1220cc;padding:6px 10px;border-radius:8px;z-index:15}
 #lg{position:fixed;bottom:12px;right:14px;font-size:11px;color:#93a1bd;background:#0a1220cc;padding:7px 11px;border-radius:8px;z-index:15}
 .sw{display:inline-block;width:13px;height:3px;border-radius:2px;margin:0 4px 0 10px;vertical-align:middle}
</style></head><body>
<div id=bar>
 <h1>&#9673; MatrAIx &nbsp;·&nbsp; Agent Interaction Network</h1>
 <span class=pill id=agents>agents &mdash;</span>
 <span class=pill id=acts>&mdash; posts &middot; &mdash; comments</span>
 <a class=pill href="/feed">&#128241; social feed &rarr;</a>
</div>
<div id=graph></div>
<div id=tip>drag to rotate &middot; scroll to zoom &middot; click an agent to inspect</div>
<div id=lg>interactions:<span class=sw style="background:#22c55e"></span>comment<span class=sw style="background:#f472b6"></span>like<span class=sw style="background:#60a5fa"></span>follow<span class=sw style="background:#eab308"></span>repost</div>
<div id=panel><span id=close onclick="document.getElementById('panel').style.display='none'">&#10005;</span><div id=pbody></div></div>
<script>
const COLOR={like_post:'#f472b6',create_comment:'#22c55e',repost:'#eab308',quote_post:'#eab308',follow:'#60a5fa',orch:'#16233d'};
function hue(id){return `hsl(${(id*47)%360} 72% 62%)`;}
const esc=t=>(t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
let threads=[];

const Graph=ForceGraph3D()(document.getElementById('graph'))
  .backgroundColor('#04060c')
  .nodeId('user_id')                 // CRITICAL: links reference user_id, not id
  .nodeLabel(n=>n.orch?'MatrAIx Orchestrator':`${n.name} — ${n.posts} posts`)
  .nodeVal(n=>n.orch?70:Math.max(4,(n.posts||1)*1.4))
  .nodeColor(n=>n.orch?'#8ab4ff':hue(n.user_id))
  .nodeOpacity(0.92)
  .nodeResolution(10)
  .linkColor(l=>l.action==='orch'?'#16233d':(COLOR[l.action]||'#666'))
  .linkWidth(l=>l.action==='orch'?0.25:Math.min(2.6,0.6+l.weight))
  .linkOpacity(0.45)
  .linkDirectionalParticles(l=>l.action==='orch'?0:2)
  .linkDirectionalParticleWidth(1.8)
  .linkDirectionalParticleSpeed(0.006)
  .warmupTicks(80).cooldownTime(9000)
  .onNodeClick(n=>{ if(n.orch){document.getElementById('panel').style.display='none';return;}
     showPanel(n); Graph.cameraPosition({x:n.x*1.35,y:n.y*1.35,z:n.z*1.35+50}, n, 800); });

async function loadGraph(){
 let gd; try{ gd=await (await fetch('/api/graph')).json(); }catch(e){ setTimeout(loadGraph,5000); return; }
 const ORCH={user_id:'orchestrator',name:'ORCHESTRATOR',orch:true};
 const nodes=[ORCH,...(gd.nodes||[])];
 const ids=new Set(nodes.map(n=>n.user_id));
 const orchE=(gd.nodes||[]).map(n=>({source:'orchestrator',target:n.user_id,action:'orch',weight:1}));
 const inter=(gd.edges||[]).filter(e=>ids.has(e.source)&&ids.has(e.target));
 document.getElementById('agents').textContent=`${(gd.nodes||[]).length} agents · ${inter.length} edges`;
 Graph.graphData({nodes,links:[...orchE,...inter]});
 setTimeout(loadGraph,8000);
}
async function loadMeta(){
 try{ const s=await (await fetch('/api/state')).json(); const st=s.platform.stats||{};
   document.getElementById('acts').textContent=`${st.post||0} posts · ${st.comment||0} comments`; }catch(e){}
 try{ threads=(await (await fetch('/api/threads')).json()).threads||[]; }catch(e){}
 setTimeout(loadMeta,4000);
}
function showPanel(n){
 const mine=threads.filter(t=>t.user_id===n.user_id).slice(0,6);
 let h=`<h3>${esc(n.name)}</h3><div class=sub>agent docker #${n.user_id} · ${n.posts} posts · ${n.followers||0} followers</div>`;
 h+= mine.length? mine.map(t=>`<div class=post>${esc(t.content).slice(0,220)}<div style="color:#5f6f8c;margin-top:4px">&#10084; ${t.num_likes} &nbsp; &#128172; ${t.num_comments}</div>`
      + (t.comments||[]).slice(0,3).map(c=>`<div class=cm><b>${esc(c.author)}:</b> ${esc(c.content).slice(0,90)}</div>`).join('')+`</div>`).join('')
   : '<div style="margin-top:8px;color:#5f6f8c">no posts in recent window</div>';
 document.getElementById('pbody').innerHTML=h;
 document.getElementById('panel').style.display='block';
}
loadGraph(); loadMeta();
</script></body></html>"""


# =====================================================================
#  /feed — social-media platform view (agent trajectories)
# =====================================================================
FEED_PAGE = """<!doctype html><html><head><meta charset=utf-8>
<title>MatrAIx — Social Feed</title>
<style>
 html,body{margin:0;min-height:100%;background:#0a0e17;color:#e6ebf5;font-family:-apple-system,Segoe UI,Roboto,sans-serif}
 #bar{position:sticky;top:0;height:46px;background:linear-gradient(90deg,#0a1424,#0a0f1c);border-bottom:1px solid #1b2740;display:flex;gap:14px;align-items:center;padding:0 18px;z-index:20}
 #bar h1{font-size:15px;margin:0;font-weight:700;background:linear-gradient(90deg,#8ab4ff,#a6f0d0);-webkit-background-clip:text;background-clip:text;color:transparent}
 .pill{background:#12203a;border:1px solid #1b2740;border-radius:20px;padding:4px 11px;font-size:12px;color:#c3cee2}
 a.pill{text-decoration:none;color:#8ab4ff}
 #wrap{max-width:680px;margin:16px auto;padding:0 14px}
 .card{background:#0e1830;border:1px solid #1c2c4a;border-radius:14px;padding:14px 16px;margin-bottom:14px}
 .rowh{display:flex;align-items:center;gap:9px}
 .av{width:34px;height:34px;border-radius:50%;flex:none;display:flex;align-items:center;justify-content:center;font-weight:700;color:#04060c;font-size:14px}
 .who{font-weight:600;font-size:14px;color:#e6ebf5}
 .hd{font-size:11px;color:#5f6f8c}
 .rp{color:#eab308;font-size:10px;border:1px solid #4a3d12;border-radius:5px;padding:1px 5px;margin-left:auto}
 .txt{font-size:14px;margin:9px 0;line-height:1.45;white-space:pre-wrap;word-break:break-word}
 .eng{font-size:12px;color:#6b7a96;display:flex;gap:16px;border-top:1px solid #16233d;padding-top:8px}
 .cm{margin:9px 0 0 20px;padding:8px 11px;background:#0b1526;border-left:2px solid #22c55e55;border-radius:0 10px 10px 0}
 .cm .rowh{gap:7px}.cm .av{width:24px;height:24px;font-size:11px}.cm .who{font-size:12.5px;color:#a6f0d0}.cm .txt{font-size:12.5px;margin:4px 0 0}
</style></head><body>
<div id=bar>
 <h1>&#128241; MatrAIx &nbsp;·&nbsp; Social Feed</h1>
 <span class=pill id=stat>&mdash;</span>
 <a class=pill href="/">&#9673; 3D network &rarr;</a>
</div>
<div id=wrap></div>
<script>
function hue(id){return `hsl(${(id*47)%360} 72% 62%)`;}
const esc=t=>(t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const ini=n=>(n||'?').trim().charAt(0).toUpperCase();
async function tick(){
 try{ const s=await (await fetch('/api/state')).json(); const st=s.platform.stats||{};
   document.getElementById('stat').textContent=`${st.user||0} agents · ${st.post||0} posts · ${st.comment||0} comments · ${st.like||0} likes`; }catch(e){}
 try{
   const d=await (await fetch('/api/threads')).json();
   document.getElementById('wrap').innerHTML=(d.threads||[]).map(t=>{
     const cms=(t.comments||[]).map(c=>`<div class=cm><div class=rowh><span class=av style="background:${hue(c.user_id)}">${ini(c.author)}</span><span class=who>${esc(c.author)}</span></div><div class=txt>${esc(c.content)}</div></div>`).join('');
     return `<div class=card><div class=rowh><span class=av style="background:${hue(t.user_id)}">${ini(t.author)}</span><div><div class=who>${esc(t.author)}</div><div class=hd>agent #${t.user_id}</div></div>${t.is_repost?'<span class=rp>repost</span>':''}</div>`
       +`<div class=txt>${esc(t.content)}</div>`
       +`<div class=eng><span>&#10084; ${t.num_likes}</span><span>&#128172; ${t.num_comments}</span><span>&#128257; ${t.num_shares}</span></div>${cms}</div>`;
   }).join('')||'<div style="color:#5f6f8c;text-align:center;margin-top:40px">waiting for posts…</div>';
 }catch(e){}
 setTimeout(tick,3000);
}
tick();
</script></body></html>"""



if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8500)
    ap.add_argument("--platform-url", default=PLATFORM_URL)
    ap.add_argument("--db-path", default=DB_PATH,
                    help="platform SQLite file (read-only fallback for the post feed)")
    args = ap.parse_args()
    PLATFORM_URL = args.platform_url
    DB_PATH = args.db_path
    uvicorn.run(app, host="0.0.0.0", port=args.port)
