# server.py — FastAPI HTTP service exposing the OASIS platform to agent containers.
# Agents connect via HTTP to perform actions, refresh feeds, and register.
# The platform owns all state and processes actions sequentially for consistency.

from __future__ import annotations

import threading
from typing import Any, Optional

from environments.oasis.platform.actions import ActionProcessor, ActionResult
from environments.oasis.platform.database import Database
from environments.oasis.platform.recsys import RecSys, RecSysType

try:
    from fastapi import FastAPI, HTTPException, Body
    from pydantic import BaseModel
    HAS_FASTAPI = True

    # NOTE: these request models MUST be module-level. Defining them inside
    # create_app() makes them function-local forward refs that FastAPI 0.136 +
    # Pydantic 2.13 cannot resolve ("... is not fully defined"), causing 500s on
    # every POST. Module scope keeps them fully defined.
    class SignupRequest(BaseModel):
        agent_id: int
        user_name: str
        name: str
        bio: str = ""

    class SignupBulkRequest(BaseModel):
        users: list[dict[str, Any]]

    class ActionRequest(BaseModel):
        user_id: int
        action_type: str
        params: Optional[dict[str, Any]] = None

    class FollowBulkRequest(BaseModel):
        edges: list[list[int]]

    class SeedPostRequest(BaseModel):
        user_id: int
        content: str
except ImportError:
    HAS_FASTAPI = False


class PlatformState:
    def __init__(self, db_path: str = ":memory:", recsys_type: str = "random", max_rec_posts: int = 50):
        self.db = Database(db_path)
        self.recsys = RecSys(self.db, RecSysType(recsys_type), max_rec_posts=max_rec_posts)
        self.action_processor = ActionProcessor(self.db)
        self._action_lock = threading.Lock()
        self._time_step = 0

    @property
    def time_step(self) -> int:
        return self._time_step

    def process_action(self, user_id: int, action_type: str, params: dict | None = None) -> ActionResult:
        with self._action_lock:
            return self.action_processor.process(user_id, action_type, params)

    def advance_step(self) -> dict[str, Any]:
        rec_count = self.recsys.update_recommendations()
        self._time_step += 1
        return {"time_step": self._time_step, "recommendations_updated": rec_count}

    def close(self):
        self.db.close()


def create_app(db_path: str = ":memory:", recsys_type: str = "random", max_rec_posts: int = 50) -> Any:
    if not HAS_FASTAPI:
        raise ImportError("fastapi and pydantic are required: pip install fastapi uvicorn pydantic")

    app = FastAPI(title="MatrAIx OASIS Platform", version="0.1.0")
    state = PlatformState(db_path=db_path, recsys_type=recsys_type, max_rec_posts=max_rec_posts)

    @app.post("/signup")
    def signup(req: SignupRequest = Body(...)):
        user_id = state.db.signup_user(req.agent_id, req.user_name, req.name, req.bio)
        return {"user_id": user_id, "agent_id": req.agent_id}

    @app.post("/signup/bulk")
    def signup_bulk(req: SignupBulkRequest = Body(...)):
        state.db.signup_users_bulk(req.users)
        return {"registered": len(req.users)}

    @app.post("/action")
    def action(req: ActionRequest = Body(...)):
        result = state.process_action(req.user_id, req.action_type, req.params)
        if not result.success and result.error:
            return {"success": False, "error": result.error}
        return result.to_dict()

    @app.post("/follow/bulk")
    def follow_bulk(req: FollowBulkRequest = Body(...)):
        edges = [(e[0], e[1]) for e in req.edges if len(e) == 2]
        state.db.add_follows_bulk(edges)
        return {"added": len(edges)}

    @app.post("/seed_post")
    def seed_post(req: SeedPostRequest = Body(...)):
        post_id = state.db.create_post(req.user_id, req.content)
        return {"post_id": post_id}

    @app.post("/step")
    def step():
        return state.advance_step()

    @app.get("/state/{agent_id}")
    def get_agent_state(agent_id: int):
        user = state.db.get_user_by_agent_id(agent_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return user

    @app.get("/user/{user_id}")
    def get_user(user_id: int):
        user = state.db.get_user(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    @app.get("/traces")
    def get_traces(user_id: int | None = None, action: str | None = None, limit: int = 1000):
        return state.db.get_traces(user_id=user_id, action=action, limit=limit)

    @app.get("/posts")
    def get_posts(limit: int = 50):
        """Recent posts (newest first) with author name, for the live feed."""
        posts = state.db.get_all_posts(limit=limit)
        users = {u["user_id"]: u for u in state.db.get_all_users()}
        feed = []
        for p in posts:
            author = users.get(p.get("user_id"), {})
            feed.append({
                "post_id": p.get("post_id"),
                "user_id": p.get("user_id"),
                "author": author.get("name") or author.get("user_name") or f"user{p.get('user_id')}",
                "content": p.get("content"),
                "quote_content": p.get("quote_content"),
                "is_repost": p.get("original_post_id") is not None,
                "num_likes": p.get("num_likes", 0),
                "num_comments": p.get("num_comments", 0),
                "num_shares": p.get("num_shares", 0),
                "created_at": p.get("created_at"),
            })
        return feed

    @app.get("/threads")
    def get_threads(limit: int = 40):
        """Recent posts as threaded conversations: each post with its author and
        nested comments (each with the commenter's name). This is the live
        social-media feed the dashboard renders over HTTP (no DB-file access)."""
        users = {u["user_id"]: (u.get("name") or u.get("user_name") or f"user{u['user_id']}")
                 for u in state.db.get_all_users()}
        posts = state.db.get_all_posts(limit=limit)
        pids = {p["post_id"] for p in posts}
        by_post: dict[int, list] = {}
        for c in state.db.get_recent_comments(limit=4000):
            if c["post_id"] in pids:
                by_post.setdefault(c["post_id"], []).append({
                    "comment_id": c["comment_id"],
                    "user_id": c["user_id"],
                    "author": users.get(c["user_id"], f"user{c['user_id']}"),
                    "content": c["content"],
                    "num_likes": c.get("num_likes", 0),
                })
        threads = []
        for p in posts:
            cs = sorted(by_post.get(p["post_id"], []), key=lambda x: x["comment_id"])
            threads.append({
                "post_id": p["post_id"],
                "user_id": p["user_id"],
                "author": users.get(p["user_id"], f"user{p['user_id']}"),
                "content": p.get("content"),
                "is_repost": p.get("original_post_id") is not None,
                "quote": p.get("quote_content"),
                "num_likes": p.get("num_likes", 0),
                "num_comments": p.get("num_comments", 0),
                "num_shares": p.get("num_shares", 0),
                "comments": cs,
            })
        return {"threads": threads}

    @app.get("/stats")
    def get_stats():
        db_stats = state.db.stats()
        db_stats["time_step"] = state.time_step
        db_stats["recsys_type"] = state.recsys.recsys_type.value
        return db_stats

    @app.get("/health")
    def health():
        return {"status": "ok", "time_step": state.time_step}

    @app.on_event("shutdown")
    def shutdown():
        state.close()

    return app
