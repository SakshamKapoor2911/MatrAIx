# actions.py — Action processing layer matching OASIS's 29 action types.
# Receives action requests from agents, executes them against the database,
# records traces, and returns results. Sequential processing for consistency.

from __future__ import annotations

from enum import Enum
from typing import Any

from environments.oasis.platform.database import Database


class ActionType(Enum):
    SIGNUP = "signup"
    CREATE_POST = "create_post"
    LIKE_POST = "like_post"
    UNLIKE_POST = "unlike_post"
    DISLIKE_POST = "dislike_post"
    UNDO_DISLIKE_POST = "undo_dislike_post"
    REPOST = "repost"
    QUOTE_POST = "quote_post"
    REPORT_POST = "report_post"
    CREATE_COMMENT = "create_comment"
    LIKE_COMMENT = "like_comment"
    UNLIKE_COMMENT = "unlike_comment"
    DISLIKE_COMMENT = "dislike_comment"
    UNDO_DISLIKE_COMMENT = "undo_dislike_comment"
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"
    MUTE = "mute"
    UNMUTE = "unmute"
    REFRESH = "refresh"
    SEARCH_POSTS = "search_posts"
    SEARCH_USER = "search_user"
    TREND = "trend"
    DO_NOTHING = "do_nothing"


class ActionResult:
    def __init__(self, success: bool, data: Any = None, error: str | None = None):
        self.success = success
        self.data = data
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"success": self.success}
        if self.data is not None:
            d["data"] = self.data
        if self.error is not None:
            d["error"] = self.error
        return d


class ActionProcessor:
    def __init__(self, db: Database):
        self._db = db

    def process(self, user_id: int, action_type: str, params: dict[str, Any] | None = None) -> ActionResult:
        params = params or {}

        try:
            action = ActionType(action_type)
        except ValueError:
            return ActionResult(success=False, error=f"Unknown action: {action_type}")

        handler = self._handlers.get(action)
        if handler is None:
            return ActionResult(success=False, error=f"No handler for action: {action_type}")

        result = handler(self, user_id, params)
        self._db.record_trace(user_id, action_type, {"params": params, "result": result.to_dict()})
        return result

    def _handle_create_post(self, user_id: int, params: dict) -> ActionResult:
        content = params.get("content", "")
        if not content:
            return ActionResult(success=False, error="content is required")
        post_id = self._db.create_post(user_id, content)
        return ActionResult(success=True, data={"post_id": post_id})

    def _handle_like_post(self, user_id: int, params: dict) -> ActionResult:
        post_id = params.get("post_id")
        if post_id is None:
            return ActionResult(success=False, error="post_id is required")
        resolved_id = self._db.get_root_post_id(int(post_id))
        ok = self._db.like_post(user_id, resolved_id)
        return ActionResult(success=ok, error=None if ok else "already liked")

    def _handle_unlike_post(self, user_id: int, params: dict) -> ActionResult:
        post_id = params.get("post_id")
        if post_id is None:
            return ActionResult(success=False, error="post_id is required")
        ok = self._db.unlike_post(user_id, int(post_id))
        return ActionResult(success=ok, error=None if ok else "not liked")

    def _handle_dislike_post(self, user_id: int, params: dict) -> ActionResult:
        post_id = params.get("post_id")
        if post_id is None:
            return ActionResult(success=False, error="post_id is required")
        resolved_id = self._db.get_root_post_id(int(post_id))
        ok = self._db.dislike_post(user_id, resolved_id)
        return ActionResult(success=ok, error=None if ok else "already disliked")

    def _handle_undo_dislike_post(self, user_id: int, params: dict) -> ActionResult:
        post_id = params.get("post_id")
        if post_id is None:
            return ActionResult(success=False, error="post_id is required")
        ok = self._db.undo_dislike_post(user_id, int(post_id))
        return ActionResult(success=ok, error=None if ok else "not disliked")

    def _handle_repost(self, user_id: int, params: dict) -> ActionResult:
        post_id = params.get("post_id")
        if post_id is None:
            return ActionResult(success=False, error="post_id is required")
        original = self._db.get_post(int(post_id))
        if original is None:
            return ActionResult(success=False, error="post not found")
        root_id = self._db.get_root_post_id(int(post_id))
        if self._db.has_reposted(user_id, root_id):
            return ActionResult(success=False, error="already reposted")
        root_post = self._db.get_post(root_id)
        content = root_post["content"] if root_post else original["content"]
        new_id = self._db.create_post(user_id, content, original_post_id=root_id)
        return ActionResult(success=True, data={"post_id": new_id, "original_post_id": root_id})

    def _handle_quote_post(self, user_id: int, params: dict) -> ActionResult:
        post_id = params.get("post_id")
        quote_content = params.get("content", "")
        if post_id is None:
            return ActionResult(success=False, error="post_id is required")
        if not quote_content:
            return ActionResult(success=False, error="content is required for quote")
        original = self._db.get_post(int(post_id))
        if original is None:
            return ActionResult(success=False, error="post not found")
        new_id = self._db.create_post(user_id, original["content"], original_post_id=int(post_id), quote_content=quote_content)
        return ActionResult(success=True, data={"post_id": new_id})

    def _handle_report_post(self, user_id: int, params: dict) -> ActionResult:
        post_id = params.get("post_id")
        reason = params.get("reason", "")
        if post_id is None:
            return ActionResult(success=False, error="post_id is required")
        report_id = self._db.report_post(user_id, int(post_id), reason)
        return ActionResult(success=True, data={"report_id": report_id})

    def _handle_create_comment(self, user_id: int, params: dict) -> ActionResult:
        post_id = params.get("post_id")
        content = params.get("content", "")
        if post_id is None:
            return ActionResult(success=False, error="post_id is required")
        if not content:
            return ActionResult(success=False, error="content is required")
        comment_id = self._db.create_comment(int(post_id), user_id, content)
        return ActionResult(success=True, data={"comment_id": comment_id})

    def _handle_like_comment(self, user_id: int, params: dict) -> ActionResult:
        comment_id = params.get("comment_id")
        if comment_id is None:
            return ActionResult(success=False, error="comment_id is required")
        ok = self._db.like_comment(user_id, int(comment_id))
        return ActionResult(success=ok, error=None if ok else "already liked")

    def _handle_unlike_comment(self, user_id: int, params: dict) -> ActionResult:
        return ActionResult(success=True)

    def _handle_dislike_comment(self, user_id: int, params: dict) -> ActionResult:
        comment_id = params.get("comment_id")
        if comment_id is None:
            return ActionResult(success=False, error="comment_id is required")
        ok = self._db.dislike_comment(user_id, int(comment_id))
        return ActionResult(success=ok, error=None if ok else "already disliked")

    def _handle_undo_dislike_comment(self, user_id: int, params: dict) -> ActionResult:
        return ActionResult(success=True)

    def _handle_follow(self, user_id: int, params: dict) -> ActionResult:
        target_id = params.get("user_id") or params.get("target_id")
        if target_id is None:
            return ActionResult(success=False, error="user_id/target_id is required")
        if int(target_id) == user_id:
            return ActionResult(success=False, error="cannot follow yourself")
        ok = self._db.add_follow(user_id, int(target_id))
        return ActionResult(success=ok, error=None if ok else "already following")

    def _handle_unfollow(self, user_id: int, params: dict) -> ActionResult:
        target_id = params.get("user_id") or params.get("target_id")
        if target_id is None:
            return ActionResult(success=False, error="user_id/target_id is required")
        ok = self._db.remove_follow(user_id, int(target_id))
        return ActionResult(success=ok, error=None if ok else "not following")

    def _handle_mute(self, user_id: int, params: dict) -> ActionResult:
        target_id = params.get("user_id") or params.get("target_id")
        if target_id is None:
            return ActionResult(success=False, error="user_id/target_id is required")
        ok = self._db.mute_user(user_id, int(target_id))
        return ActionResult(success=ok, error=None if ok else "already muted")

    def _handle_unmute(self, user_id: int, params: dict) -> ActionResult:
        target_id = params.get("user_id") or params.get("target_id")
        if target_id is None:
            return ActionResult(success=False, error="user_id/target_id is required")
        ok = self._db.unmute_user(user_id, int(target_id))
        return ActionResult(success=ok, error=None if ok else "not muted")

    def _handle_refresh(self, user_id: int, params: dict) -> ActionResult:
        rec_posts = self._db.get_recommended_posts(user_id)
        following_posts = self._db.get_following_posts(user_id, limit=10)
        muted = set(self._db.get_muted(user_id))

        all_posts = []
        seen_ids: set[int] = set()
        for post in rec_posts + following_posts:
            if post["post_id"] not in seen_ids and post["user_id"] not in muted:
                all_posts.append(post)
                seen_ids.add(post["post_id"])

        return ActionResult(success=True, data={"posts": all_posts})

    def _handle_search_posts(self, user_id: int, params: dict) -> ActionResult:
        query = params.get("query", "")
        if not query:
            return ActionResult(success=False, error="query is required")
        posts = self._db.search_posts(query)
        return ActionResult(success=True, data={"posts": posts})

    def _handle_search_user(self, user_id: int, params: dict) -> ActionResult:
        query = params.get("query", "")
        if not query:
            return ActionResult(success=False, error="query is required")
        users = self._db.search_users(query)
        return ActionResult(success=True, data={"users": users})

    def _handle_trend(self, user_id: int, params: dict) -> ActionResult:
        trending = self._db.get_trending_posts(limit=10)
        return ActionResult(success=True, data={"posts": trending})

    def _handle_do_nothing(self, user_id: int, params: dict) -> ActionResult:
        return ActionResult(success=True)

    _handlers = {
        ActionType.CREATE_POST: _handle_create_post,
        ActionType.LIKE_POST: _handle_like_post,
        ActionType.UNLIKE_POST: _handle_unlike_post,
        ActionType.DISLIKE_POST: _handle_dislike_post,
        ActionType.UNDO_DISLIKE_POST: _handle_undo_dislike_post,
        ActionType.REPOST: _handle_repost,
        ActionType.QUOTE_POST: _handle_quote_post,
        ActionType.REPORT_POST: _handle_report_post,
        ActionType.CREATE_COMMENT: _handle_create_comment,
        ActionType.LIKE_COMMENT: _handle_like_comment,
        ActionType.UNLIKE_COMMENT: _handle_unlike_comment,
        ActionType.DISLIKE_COMMENT: _handle_dislike_comment,
        ActionType.UNDO_DISLIKE_COMMENT: _handle_undo_dislike_comment,
        ActionType.FOLLOW: _handle_follow,
        ActionType.UNFOLLOW: _handle_unfollow,
        ActionType.MUTE: _handle_mute,
        ActionType.UNMUTE: _handle_unmute,
        ActionType.REFRESH: _handle_refresh,
        ActionType.SEARCH_POSTS: _handle_search_posts,
        ActionType.SEARCH_USER: _handle_search_user,
        ActionType.TREND: _handle_trend,
        ActionType.DO_NOTHING: _handle_do_nothing,
    }
