# app.py — FastAPI backend for the OASIS simulation dashboard.
# Serves real-time simulation data from SQLite and static frontend files.
# Endpoints provide agents, posts, traces, network, stats, and persona info.

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).parent / "static"


def create_dashboard_app(db_path: str = "environments/oasis/output/simulation.db") -> FastAPI:
    app = FastAPI(title="MatrAIx OASIS Dashboard", version="0.1.0")
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    def _query(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def _query_one(sql: str, params: tuple = ()) -> dict[str, Any] | None:
        rows = _query(sql, params)
        return rows[0] if rows else None

    @app.get("/", response_class=HTMLResponse)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/stats")
    def get_stats():
        tables = ["user", "post", "follow", '"like"', "dislike", "comment", "trace", "rec"]
        stats = {}
        for table in tables:
            row = _query_one(f"SELECT COUNT(*) as cnt FROM {table}")
            stats[table.strip('"')] = row["cnt"] if row else 0
        return stats

    @app.get("/api/agents")
    def get_agents():
        users = _query("SELECT * FROM user ORDER BY user_id")
        for u in users:
            posts = _query("SELECT COUNT(*) as cnt FROM post WHERE user_id = ?", (u["user_id"],))
            u["post_count"] = posts[0]["cnt"] if posts else 0
            likes_given = _query('SELECT COUNT(*) as cnt FROM "like" WHERE user_id = ?', (u["user_id"],))
            u["likes_given"] = likes_given[0]["cnt"] if likes_given else 0
        return users

    @app.get("/api/agent/{user_id}")
    def get_agent(user_id: int):
        user = _query_one("SELECT * FROM user WHERE user_id = ?", (user_id,))
        if not user:
            return {"error": "not found"}
        user["posts"] = _query("SELECT * FROM post WHERE user_id = ? ORDER BY created_at DESC LIMIT 20", (user_id,))
        user["traces"] = _query("SELECT * FROM trace WHERE user_id = ? ORDER BY trace_id DESC LIMIT 50", (user_id,))
        user["following"] = _query("SELECT followee_id FROM follow WHERE follower_id = ?", (user_id,))
        user["followers"] = _query("SELECT follower_id FROM follow WHERE followee_id = ?", (user_id,))
        return user

    @app.get("/api/posts")
    def get_posts(limit: int = Query(50), offset: int = Query(0)):
        posts = _query("SELECT * FROM post ORDER BY post_id DESC LIMIT ? OFFSET ?", (limit, offset))
        for p in posts:
            p["comments"] = _query("SELECT * FROM comment WHERE post_id = ? ORDER BY created_at", (p["post_id"],))
        return posts

    @app.get("/api/feed")
    def get_feed():
        return _query("SELECT p.*, u.name, u.user_name FROM post p JOIN user u ON p.user_id = u.user_id ORDER BY p.post_id DESC LIMIT 100")

    @app.get("/api/traces")
    def get_traces(limit: int = Query(200), action: Optional[str] = None):
        if action:
            return _query("SELECT * FROM trace WHERE action = ? ORDER BY trace_id DESC LIMIT ?", (action, limit))
        return _query("SELECT * FROM trace ORDER BY trace_id DESC LIMIT ?", (limit,))

    @app.get("/api/network")
    def get_network():
        nodes = _query("SELECT user_id, user_name, name, num_followers, num_followings FROM user")
        edges = _query("SELECT follower_id as source, followee_id as target FROM follow")
        return {"nodes": nodes, "edges": edges}

    @app.get("/api/timeline")
    def get_timeline():
        actions = _query("SELECT action, COUNT(*) as cnt FROM trace GROUP BY action ORDER BY cnt DESC")
        posts_over_time = _query("SELECT created_at, COUNT(*) as cnt FROM post GROUP BY created_at ORDER BY created_at")
        return {"action_distribution": actions, "posts_over_time": posts_over_time}

    @app.get("/api/action_distribution")
    def get_action_distribution():
        return _query("SELECT action, COUNT(*) as cnt FROM trace WHERE action != 'refresh' GROUP BY action ORDER BY cnt DESC")

    @app.get("/api/engagement")
    def get_engagement():
        return _query("""
            SELECT u.user_id, u.name, u.user_name,
                   (SELECT COUNT(*) FROM post WHERE user_id = u.user_id) as posts,
                   (SELECT COUNT(*) FROM "like" WHERE user_id = u.user_id) as likes_given,
                   (SELECT COUNT(*) FROM follow WHERE follower_id = u.user_id) as following,
                   u.num_followers as followers
            FROM user u ORDER BY posts DESC
        """)

    return app


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="environments/oasis/output/simulation.db")
    parser.add_argument("--port", type=int, default=3000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    app = create_dashboard_app(db_path=args.db)
    print(f"Dashboard: http://localhost:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)
