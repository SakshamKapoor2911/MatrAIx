# database.py — SQLite database layer matching OASIS's 16-table schema.
# All state (users, posts, follows, likes, comments, traces) lives here.
# Uses synchronous SQLite with WAL mode for concurrent reads from agent containers.

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS user (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER UNIQUE NOT NULL,
    user_name TEXT NOT NULL,
    name TEXT NOT NULL,
    bio TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    num_followings INTEGER DEFAULT 0,
    num_followers INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS post (
    post_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    original_post_id INTEGER DEFAULT NULL,
    quote_content TEXT DEFAULT NULL,
    created_at TEXT NOT NULL,
    num_likes INTEGER DEFAULT 0,
    num_dislikes INTEGER DEFAULT 0,
    num_shares INTEGER DEFAULT 0,
    num_comments INTEGER DEFAULT 0,
    num_reports INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES user(user_id)
);

CREATE TABLE IF NOT EXISTS follow (
    follow_id INTEGER PRIMARY KEY AUTOINCREMENT,
    follower_id INTEGER NOT NULL,
    followee_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(follower_id, followee_id),
    FOREIGN KEY (follower_id) REFERENCES user(user_id),
    FOREIGN KEY (followee_id) REFERENCES user(user_id)
);

CREATE TABLE IF NOT EXISTS "like" (
    like_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    post_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, post_id),
    FOREIGN KEY (user_id) REFERENCES user(user_id),
    FOREIGN KEY (post_id) REFERENCES post(post_id)
);

CREATE TABLE IF NOT EXISTS dislike (
    dislike_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    post_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, post_id),
    FOREIGN KEY (user_id) REFERENCES user(user_id),
    FOREIGN KEY (post_id) REFERENCES post(post_id)
);

CREATE TABLE IF NOT EXISTS comment (
    comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    num_likes INTEGER DEFAULT 0,
    num_dislikes INTEGER DEFAULT 0,
    FOREIGN KEY (post_id) REFERENCES post(post_id),
    FOREIGN KEY (user_id) REFERENCES user(user_id)
);

CREATE TABLE IF NOT EXISTS comment_like (
    comment_like_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    comment_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, comment_id)
);

CREATE TABLE IF NOT EXISTS comment_dislike (
    comment_dislike_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    comment_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, comment_id)
);

CREATE TABLE IF NOT EXISTS mute (
    mute_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    mutee_id INTEGER NOT NULL,
    UNIQUE(user_id, mutee_id)
);

CREATE TABLE IF NOT EXISTS rec (
    user_id INTEGER NOT NULL,
    post_id INTEGER NOT NULL,
    UNIQUE(user_id, post_id)
);

CREATE TABLE IF NOT EXISTS trace (
    trace_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    info TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS report (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    post_id INTEGER NOT NULL,
    reason TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS product (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    description TEXT DEFAULT '',
    price REAL DEFAULT 0.0,
    sales INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS chat_group (
    group_id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS group_member (
    group_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    joined_at TEXT NOT NULL,
    UNIQUE(group_id, user_id)
);

CREATE TABLE IF NOT EXISTS group_message (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_post_user ON post(user_id);
CREATE INDEX IF NOT EXISTS idx_post_created ON post(created_at);
CREATE INDEX IF NOT EXISTS idx_follow_follower ON follow(follower_id);
CREATE INDEX IF NOT EXISTS idx_follow_followee ON follow(followee_id);
CREATE INDEX IF NOT EXISTS idx_like_post ON "like"(post_id);
CREATE INDEX IF NOT EXISTS idx_like_user ON "like"(user_id);
CREATE INDEX IF NOT EXISTS idx_comment_post ON comment(post_id);
CREATE INDEX IF NOT EXISTS idx_trace_user ON trace(user_id);
CREATE INDEX IF NOT EXISTS idx_trace_action ON trace(action);
CREATE INDEX IF NOT EXISTS idx_rec_user ON rec(user_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, db_path: str | Path = ":memory:"):
        self._db_path = str(db_path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA cache_size=-64000")
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    def close(self):
        self._conn.close()

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cursor = self._conn.execute(sql, params)
            self._conn.commit()
            return cursor

    def _execute_many(self, sql: str, params_list: list[tuple]) -> None:
        with self._lock:
            self._conn.executemany(sql, params_list)
            self._conn.commit()

    def _query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with self._lock:
            cursor = self._conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def _query_one(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        with self._lock:
            cursor = self._conn.execute(sql, params)
            row = cursor.fetchone()
            return dict(row) if row else None

    def signup_user(self, agent_id: int, user_name: str, name: str, bio: str = "") -> int:
        cursor = self._execute(
            "INSERT INTO user (agent_id, user_name, name, bio, created_at) VALUES (?, ?, ?, ?, ?)",
            (agent_id, user_name, name, bio, _now()),
        )
        return cursor.lastrowid

    def signup_users_bulk(self, users: list[dict[str, Any]]) -> None:
        now = _now()
        params = [(u["agent_id"], u["user_name"], u["name"], u.get("bio", ""), now) for u in users]
        self._execute_many(
            "INSERT OR IGNORE INTO user (agent_id, user_name, name, bio, created_at) VALUES (?, ?, ?, ?, ?)",
            params,
        )

    def add_follow(self, follower_id: int, followee_id: int) -> bool:
        try:
            self._execute(
                "INSERT INTO follow (follower_id, followee_id, created_at) VALUES (?, ?, ?)",
                (follower_id, followee_id, _now()),
            )
            self._execute("UPDATE user SET num_followings = num_followings + 1 WHERE user_id = ?", (follower_id,))
            self._execute("UPDATE user SET num_followers = num_followers + 1 WHERE user_id = ?", (followee_id,))
            return True
        except sqlite3.IntegrityError:
            return False

    def add_follows_bulk(self, edges: list[tuple[int, int]]) -> None:
        now = _now()
        params = [(f, t, now) for f, t in edges]
        self._execute_many("INSERT OR IGNORE INTO follow (follower_id, followee_id, created_at) VALUES (?, ?, ?)", params)

    def remove_follow(self, follower_id: int, followee_id: int) -> bool:
        result = self._execute(
            "DELETE FROM follow WHERE follower_id = ? AND followee_id = ?",
            (follower_id, followee_id),
        )
        if result.rowcount > 0:
            self._execute("UPDATE user SET num_followings = num_followings - 1 WHERE user_id = ?", (follower_id,))
            self._execute("UPDATE user SET num_followers = num_followers - 1 WHERE user_id = ?", (followee_id,))
            return True
        return False

    def create_post(self, user_id: int, content: str, original_post_id: int | None = None, quote_content: str | None = None) -> int:
        cursor = self._execute(
            "INSERT INTO post (user_id, content, original_post_id, quote_content, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, content, original_post_id, quote_content, _now()),
        )
        if original_post_id is not None:
            self._execute("UPDATE post SET num_shares = num_shares + 1 WHERE post_id = ?", (original_post_id,))
        return cursor.lastrowid

    def like_post(self, user_id: int, post_id: int) -> bool:
        try:
            self._execute(
                'INSERT INTO "like" (user_id, post_id, created_at) VALUES (?, ?, ?)',
                (user_id, post_id, _now()),
            )
            self._execute("UPDATE post SET num_likes = num_likes + 1 WHERE post_id = ?", (post_id,))
            return True
        except sqlite3.IntegrityError:
            return False

    def unlike_post(self, user_id: int, post_id: int) -> bool:
        result = self._execute('DELETE FROM "like" WHERE user_id = ? AND post_id = ?', (user_id, post_id))
        if result.rowcount > 0:
            self._execute("UPDATE post SET num_likes = num_likes - 1 WHERE post_id = ?", (post_id,))
            return True
        return False

    def dislike_post(self, user_id: int, post_id: int) -> bool:
        try:
            self._execute(
                "INSERT INTO dislike (user_id, post_id, created_at) VALUES (?, ?, ?)",
                (user_id, post_id, _now()),
            )
            self._execute("UPDATE post SET num_dislikes = num_dislikes + 1 WHERE post_id = ?", (post_id,))
            return True
        except sqlite3.IntegrityError:
            return False

    def undo_dislike_post(self, user_id: int, post_id: int) -> bool:
        result = self._execute("DELETE FROM dislike WHERE user_id = ? AND post_id = ?", (user_id, post_id))
        if result.rowcount > 0:
            self._execute("UPDATE post SET num_dislikes = num_dislikes - 1 WHERE post_id = ?", (post_id,))
            return True
        return False

    def create_comment(self, post_id: int, user_id: int, content: str) -> int:
        cursor = self._execute(
            "INSERT INTO comment (post_id, user_id, content, created_at) VALUES (?, ?, ?, ?)",
            (post_id, user_id, content, _now()),
        )
        self._execute("UPDATE post SET num_comments = num_comments + 1 WHERE post_id = ?", (post_id,))
        return cursor.lastrowid

    def like_comment(self, user_id: int, comment_id: int) -> bool:
        try:
            self._execute(
                "INSERT INTO comment_like (user_id, comment_id, created_at) VALUES (?, ?, ?)",
                (user_id, comment_id, _now()),
            )
            self._execute("UPDATE comment SET num_likes = num_likes + 1 WHERE comment_id = ?", (comment_id,))
            return True
        except sqlite3.IntegrityError:
            return False

    def dislike_comment(self, user_id: int, comment_id: int) -> bool:
        try:
            self._execute(
                "INSERT INTO comment_dislike (user_id, comment_id, created_at) VALUES (?, ?, ?)",
                (user_id, comment_id, _now()),
            )
            self._execute("UPDATE comment SET num_dislikes = num_dislikes + 1 WHERE comment_id = ?", (comment_id,))
            return True
        except sqlite3.IntegrityError:
            return False

    def mute_user(self, user_id: int, mutee_id: int) -> bool:
        try:
            self._execute("INSERT INTO mute (user_id, mutee_id) VALUES (?, ?)", (user_id, mutee_id))
            return True
        except sqlite3.IntegrityError:
            return False

    def unmute_user(self, user_id: int, mutee_id: int) -> bool:
        result = self._execute("DELETE FROM mute WHERE user_id = ? AND mutee_id = ?", (user_id, mutee_id))
        return result.rowcount > 0

    def get_user(self, user_id: int) -> dict[str, Any] | None:
        return self._query_one("SELECT * FROM user WHERE user_id = ?", (user_id,))

    def get_user_by_agent_id(self, agent_id: int) -> dict[str, Any] | None:
        return self._query_one("SELECT * FROM user WHERE agent_id = ?", (agent_id,))

    def get_all_users(self) -> list[dict[str, Any]]:
        return self._query("SELECT * FROM user")

    def get_post(self, post_id: int) -> dict[str, Any] | None:
        return self._query_one("SELECT * FROM post WHERE post_id = ?", (post_id,))

    def get_posts_by_user(self, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        return self._query("SELECT * FROM post WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit))

    def get_following_posts(self, user_id: int, limit: int = 20) -> list[dict[str, Any]]:
        return self._query(
            """SELECT p.* FROM post p
               JOIN follow f ON p.user_id = f.followee_id
               WHERE f.follower_id = ?
               ORDER BY p.num_likes DESC, p.created_at DESC
               LIMIT ?""",
            (user_id, limit),
        )

    def get_recommended_posts(self, user_id: int) -> list[dict[str, Any]]:
        return self._query(
            """SELECT p.* FROM post p
               JOIN rec r ON p.post_id = r.post_id
               WHERE r.user_id = ?
               ORDER BY p.created_at DESC""",
            (user_id,),
        )

    def get_followees(self, user_id: int) -> list[int]:
        rows = self._query("SELECT followee_id FROM follow WHERE follower_id = ?", (user_id,))
        return [r["followee_id"] for r in rows]

    def get_followers(self, user_id: int) -> list[int]:
        rows = self._query("SELECT follower_id FROM follow WHERE followee_id = ?", (user_id,))
        return [r["follower_id"] for r in rows]

    def get_muted(self, user_id: int) -> list[int]:
        rows = self._query("SELECT mutee_id FROM mute WHERE user_id = ?", (user_id,))
        return [r["mutee_id"] for r in rows]

    def get_root_post_id(self, post_id: int) -> int:
        post = self.get_post(post_id)
        if post is None:
            return post_id
        original = post.get("original_post_id")
        if original is None:
            return post_id
        return original

    def is_repost(self, post_id: int) -> bool:
        post = self.get_post(post_id)
        if post is None:
            return False
        return post.get("original_post_id") is not None and post.get("quote_content") is None

    def has_reposted(self, user_id: int, original_post_id: int) -> bool:
        row = self._query_one(
            "SELECT post_id FROM post WHERE user_id = ? AND original_post_id = ?",
            (user_id, original_post_id),
        )
        return row is not None

    def get_all_posts(self, limit: int = 10000) -> list[dict[str, Any]]:
        return self._query("SELECT * FROM post ORDER BY created_at DESC LIMIT ?", (limit,))

    def get_comments_for_post(self, post_id: int) -> list[dict[str, Any]]:
        return self._query("SELECT * FROM comment WHERE post_id = ? ORDER BY created_at", (post_id,))

    def clear_rec_table(self) -> None:
        self._execute("DELETE FROM rec")

    def set_recommendations(self, recs: list[tuple[int, int]]) -> None:
        self._execute("DELETE FROM rec")
        if recs:
            self._execute_many("INSERT OR IGNORE INTO rec (user_id, post_id) VALUES (?, ?)", recs)

    def record_trace(self, user_id: int, action: str, info: dict[str, Any] | None = None) -> int:
        cursor = self._execute(
            "INSERT INTO trace (user_id, action, info, created_at) VALUES (?, ?, ?, ?)",
            (user_id, action, json.dumps(info or {}), _now()),
        )
        return cursor.lastrowid

    def get_traces(self, user_id: int | None = None, action: str | None = None, limit: int = 10000) -> list[dict[str, Any]]:
        sql = "SELECT * FROM trace WHERE 1=1"
        params: list[Any] = []
        if user_id is not None:
            sql += " AND user_id = ?"
            params.append(user_id)
        if action is not None:
            sql += " AND action = ?"
            params.append(action)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return self._query(sql, tuple(params))

    def get_all_traces(self) -> list[dict[str, Any]]:
        return self._query("SELECT * FROM trace ORDER BY trace_id")

    def search_posts(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._query(
            "SELECT * FROM post WHERE content LIKE ? ORDER BY num_likes DESC LIMIT ?",
            (f"%{query}%", limit),
        )

    def search_users(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._query(
            "SELECT * FROM user WHERE user_name LIKE ? OR name LIKE ? LIMIT ?",
            (f"%{query}%", f"%{query}%", limit),
        )

    def get_trending_posts(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._query(
            "SELECT * FROM post ORDER BY (num_likes + num_shares + num_comments) DESC LIMIT ?",
            (limit,),
        )

    def report_post(self, user_id: int, post_id: int, reason: str = "") -> int:
        cursor = self._execute(
            "INSERT INTO report (user_id, post_id, reason) VALUES (?, ?, ?)",
            (user_id, post_id, reason),
        )
        return cursor.lastrowid

    def stats(self) -> dict[str, int]:
        counts = {}
        for table in ["user", "post", "follow", '"like"', "dislike", "comment", "trace", "rec"]:
            row = self._query_one(f"SELECT COUNT(*) as cnt FROM {table}")
            key = table.strip('"')
            counts[key] = row["cnt"] if row else 0
        return counts
