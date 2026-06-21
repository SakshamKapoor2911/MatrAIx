# run_full_simulation.py — Complete end-to-end simulation with 20 agents, 10 steps,
# full trajectory collection, and visualization generation.

import sys
import json
import time
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from environments.oasis.agents.orchestrator import Orchestrator, SimulationConfig
from environments.oasis.persona_loader import load_personas_from_directory
from environments.oasis.network import build_social_graph, NetworkConfig, graph_stats

OUTPUT_DIR = Path("environments/oasis/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NUM_AGENTS = 20
NUM_STEPS = 10
LLM_URL = "http://localhost:8002/v1"
LLM_MODEL = "Qwen/Qwen3-8B"

print("=" * 100)
print(f"MATRAIX OASIS SIMULATION — {NUM_AGENTS} agents x {NUM_STEPS} steps x {LLM_MODEL}")
print("=" * 100)

print("\n[1/6] Loading personas...")
personas = load_personas_from_directory("personas/Jun20_1k_persona_description/", max_agents=NUM_AGENTS)
print(f"  Loaded {len(personas)} personas:")
for i, p in enumerate(personas):
    print(f"    {i+1:02d} | {p.name:20s} | {p.profession:30s} | {p.mbti} | {p.country}")

print("\n[2/6] Building social graph...")
graph = build_social_graph(personas, NetworkConfig(random_seed=42))
stats = graph_stats(graph)
print(f"  Edges: {stats['num_edges']}, Influencers: {stats['num_influencers']}")
print(f"  Clusters: {stats['topic_cluster_sizes']}")
print(f"  Seed posts: {stats['num_seed_posts']}")

print("\n[3/6] Configuring simulation...")
config = SimulationConfig(
    max_agents=NUM_AGENTS,
    num_steps=NUM_STEPS,
    llm_base_url=LLM_URL,
    llm_api_key="no-key",
    llm_model=LLM_MODEL,
    llm_temperature=0.9,
    recsys_type="random",
    available_actions=["create_post", "like_post", "dislike_post", "repost", "follow", "create_comment", "do_nothing"],
)

orch = Orchestrator(config)
orch.setup(personas=personas, graph=graph)

print(f"\n[4/6] Running simulation ({NUM_STEPS} steps)...")
start = time.time()
result = orch.run()
elapsed = time.time() - start
print(f"  Completed in {elapsed:.1f}s ({elapsed/NUM_STEPS:.1f}s/step)")

print("\n[5/6] Collecting results...")
print(f"\n  PLATFORM STATS:")
for k, v in result.platform_stats.items():
    print(f"    {k:12s}: {v}")

traces = orch.get_traces()
print(f"\n  TRAJECTORIES: {len(traces)} total actions")

action_counts = {}
for t in traces:
    a = t["action"]
    action_counts[a] = action_counts.get(a, 0) + 1

print(f"\n  ACTION DISTRIBUTION:")
for a, c in sorted(action_counts.items(), key=lambda x: -x[1]):
    pct = c / len(traces) * 100
    bar = "#" * int(pct / 2)
    print(f"    {a:15s}: {c:4d} ({pct:5.1f}%) {bar}")

per_user_posts = {}
for t in traces:
    if t["action"] == "create_post":
        uid = t["user_id"]
        per_user_posts[uid] = per_user_posts.get(uid, 0) + 1

print(f"\n  POSTS PER AGENT:")
for uid in sorted(per_user_posts.keys()):
    p = personas[uid - 1] if uid <= len(personas) else None
    name = p.name if p else f"user_{uid}"
    print(f"    user_{uid:02d} ({name:18s}): {per_user_posts[uid]} posts")

posts = orch._platform_state.db.get_all_posts(limit=50)
print(f"\n  SAMPLE POSTS (first 15):")
print("  " + "-" * 95)
for p in sorted(posts, key=lambda x: x["post_id"])[:15]:
    content = (p["content"] or "")[:85]
    rt = f" [REPOST #{p['original_post_id']}]" if p["original_post_id"] else ""
    print(f"    #{p['post_id']:02d} user_{p['user_id']:02d} | L:{p['num_likes']} D:{p['num_dislikes']} S:{p['num_shares']} C:{p['num_comments']}{rt} | {content}")
print("  " + "-" * 95)

print("\n[6/6] Saving outputs...")

traces_path = OUTPUT_DIR / "traces.json"
with open(traces_path, "w") as f:
    json.dump(traces, f, indent=2)
print(f"  Traces: {traces_path} ({len(traces)} records)")

posts_path = OUTPUT_DIR / "posts.json"
with open(posts_path, "w") as f:
    json.dump(posts, f, indent=2, default=str)
print(f"  Posts: {posts_path} ({len(posts)} records)")

summary = {
    "num_agents": NUM_AGENTS,
    "num_steps": NUM_STEPS,
    "model": LLM_MODEL,
    "duration_seconds": elapsed,
    "platform_stats": result.platform_stats,
    "action_distribution": action_counts,
    "posts_per_user": per_user_posts,
    "graph_stats": stats,
}
summary_path = OUTPUT_DIR / "summary.json"
with open(summary_path, "w") as f:
    json.dump(summary, f, indent=2)
print(f"  Summary: {summary_path}")

db_path = OUTPUT_DIR / "simulation.db"
import shutil
if orch._platform_state and orch._platform_state.db._db_path == ":memory:":
    conn_src = orch._platform_state.db._conn
    conn_dst = sqlite3.connect(str(db_path))
    conn_src.backup(conn_dst)
    conn_dst.close()
    print(f"  Database: {db_path}")

orch.close()

print("\n" + "=" * 100)
print("SIMULATION COMPLETE")
print(f"  Output directory: {OUTPUT_DIR}")
print(f"  Total actions: {len(traces)}")
print(f"  Total posts: {len(posts)}")
print(f"  Duration: {elapsed:.1f}s")
print("=" * 100)
