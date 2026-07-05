# test_platform.py — Tests for the platform module (database, actions, recsys, server).
# Validates the full OASIS-compatible state layer: 16-table schema, action processing,
# trace recording, recommendation algorithms, and the HTTP API contract.

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from environments.oasis.platform.database import Database
from environments.oasis.platform.actions import ActionProcessor
from environments.oasis.platform.recsys import RecSys, RecSysType
from environments.oasis.platform.server import PlatformState, create_app


@pytest.fixture
def db():
    d = Database(":memory:")
    yield d
    d.close()


@pytest.fixture
def populated_db(db):
    db.signup_user(0, "alice_01", "Alice", "Tech enthusiast")
    db.signup_user(1, "bob_02", "Bob", "Finance pro")
    db.signup_user(2, "carol_03", "Carol", "Designer")
    db.add_follow(1, 2)
    db.add_follow(1, 3)
    db.add_follow(2, 1)
    db.create_post(1, "Hello world from Alice!")
    db.create_post(2, "Markets are up today")
    db.create_post(3, "New design trends for 2026")
    return db


class TestDatabase:
    def test_signup_user(self, db):
        uid = db.signup_user(0, "test_user", "Test User", "bio here")
        assert uid == 1
        user = db.get_user(uid)
        assert user["user_name"] == "test_user"
        assert user["name"] == "Test User"
        assert user["bio"] == "bio here"

    def test_signup_bulk(self, db):
        users = [
            {"agent_id": 0, "user_name": "a", "name": "A"},
            {"agent_id": 1, "user_name": "b", "name": "B"},
            {"agent_id": 2, "user_name": "c", "name": "C"},
        ]
        db.signup_users_bulk(users)
        all_users = db.get_all_users()
        assert len(all_users) == 3

    def test_create_post(self, db):
        db.signup_user(0, "u", "U")
        pid = db.create_post(1, "Hello!")
        post = db.get_post(pid)
        assert post["content"] == "Hello!"
        assert post["user_id"] == 1
        assert post["num_likes"] == 0

    def test_like_post(self, db):
        db.signup_user(0, "u", "U")
        db.signup_user(1, "v", "V")
        pid = db.create_post(1, "Post")
        assert db.like_post(2, pid) is True
        post = db.get_post(pid)
        assert post["num_likes"] == 1
        assert db.like_post(2, pid) is False

    def test_unlike_post(self, db):
        db.signup_user(0, "u", "U")
        pid = db.create_post(1, "Post")
        db.like_post(1, pid)
        assert db.unlike_post(1, pid) is True
        post = db.get_post(pid)
        assert post["num_likes"] == 0

    def test_dislike_post(self, db):
        db.signup_user(0, "u", "U")
        pid = db.create_post(1, "Post")
        assert db.dislike_post(1, pid) is True
        post = db.get_post(pid)
        assert post["num_dislikes"] == 1

    def test_follow_unfollow(self, db):
        db.signup_user(0, "a", "A")
        db.signup_user(1, "b", "B")
        assert db.add_follow(1, 2) is True
        assert db.add_follow(1, 2) is False
        followees = db.get_followees(1)
        assert 2 in followees
        assert db.remove_follow(1, 2) is True
        followees = db.get_followees(1)
        assert 2 not in followees

    def test_create_comment(self, db):
        db.signup_user(0, "u", "U")
        pid = db.create_post(1, "Post")
        cid = db.create_comment(pid, 1, "Nice post!")
        assert cid == 1
        comments = db.get_comments_for_post(pid)
        assert len(comments) == 1
        assert comments[0]["content"] == "Nice post!"
        post = db.get_post(pid)
        assert post["num_comments"] == 1

    def test_mute_unmute(self, db):
        db.signup_user(0, "a", "A")
        db.signup_user(1, "b", "B")
        assert db.mute_user(1, 2) is True
        assert db.mute_user(1, 2) is False
        muted = db.get_muted(1)
        assert 2 in muted
        assert db.unmute_user(1, 2) is True
        muted = db.get_muted(1)
        assert 2 not in muted

    def test_repost_increments_shares(self, db):
        db.signup_user(0, "u", "U")
        db.signup_user(1, "v", "V")
        pid = db.create_post(1, "Original")
        db.create_post(2, "Original", original_post_id=pid)
        post = db.get_post(pid)
        assert post["num_shares"] == 1

    def test_record_trace(self, db):
        db.signup_user(0, "u", "U")
        tid = db.record_trace(1, "create_post", {"content": "hello"})
        assert tid == 1
        traces = db.get_traces(user_id=1)
        assert len(traces) == 1
        assert traces[0]["action"] == "create_post"

    def test_search_posts(self, populated_db):
        results = populated_db.search_posts("markets")
        assert len(results) >= 1
        assert "Markets" in results[0]["content"]

    def test_search_users(self, populated_db):
        results = populated_db.search_users("alice")
        assert len(results) >= 1

    def test_trending_posts(self, populated_db):
        populated_db.like_post(2, 1)
        populated_db.like_post(3, 1)
        trending = populated_db.get_trending_posts(limit=3)
        assert trending[0]["post_id"] == 1

    def test_recommendations(self, populated_db):
        populated_db.set_recommendations([(1, 2), (1, 3)])
        recs = populated_db.get_recommended_posts(1)
        assert len(recs) == 2
        # With an empty rec table, the feed now falls back to recent posts from
        # OTHER users (keeps agent feeds live when recsys never runs), so it is
        # no longer empty; it must simply exclude the requesting user's own posts.
        populated_db.clear_rec_table()
        recs = populated_db.get_recommended_posts(1)
        assert all(p["user_id"] != 1 for p in recs)

    def test_stats(self, populated_db):
        stats = populated_db.stats()
        assert stats["user"] == 3
        assert stats["post"] == 3
        assert stats["follow"] == 3

    def test_following_posts(self, populated_db):
        posts = populated_db.get_following_posts(1)
        assert len(posts) >= 1


class TestActionProcessor:
    def test_create_post(self, db):
        db.signup_user(0, "u", "U")
        proc = ActionProcessor(db)
        result = proc.process(1, "create_post", {"content": "Test post"})
        assert result.success is True
        assert result.data["post_id"] == 1

    def test_create_post_empty_content(self, db):
        db.signup_user(0, "u", "U")
        proc = ActionProcessor(db)
        result = proc.process(1, "create_post", {"content": ""})
        assert result.success is False

    def test_like_post(self, db):
        db.signup_user(0, "u", "U")
        db.create_post(1, "Post")
        proc = ActionProcessor(db)
        result = proc.process(1, "like_post", {"post_id": 1})
        assert result.success is True

    def test_follow(self, db):
        db.signup_user(0, "a", "A")
        db.signup_user(1, "b", "B")
        proc = ActionProcessor(db)
        result = proc.process(1, "follow", {"user_id": 2})
        assert result.success is True

    def test_follow_self_fails(self, db):
        db.signup_user(0, "a", "A")
        proc = ActionProcessor(db)
        result = proc.process(1, "follow", {"user_id": 1})
        assert result.success is False

    def test_refresh(self, populated_db):
        populated_db.set_recommendations([(1, 2), (1, 3)])
        proc = ActionProcessor(populated_db)
        result = proc.process(1, "refresh", {})
        assert result.success is True
        assert "posts" in result.data
        assert len(result.data["posts"]) >= 1

    def test_refresh_excludes_muted(self, populated_db):
        populated_db.set_recommendations([(1, 1), (1, 2), (1, 3)])
        populated_db.mute_user(1, 3)
        proc = ActionProcessor(populated_db)
        result = proc.process(1, "refresh", {})
        post_user_ids = [p["user_id"] for p in result.data["posts"]]
        assert 3 not in post_user_ids

    def test_do_nothing(self, db):
        db.signup_user(0, "u", "U")
        proc = ActionProcessor(db)
        result = proc.process(1, "do_nothing", {})
        assert result.success is True

    def test_unknown_action(self, db):
        db.signup_user(0, "u", "U")
        proc = ActionProcessor(db)
        result = proc.process(1, "fly_to_moon", {})
        assert result.success is False

    def test_repost(self, db):
        db.signup_user(0, "u", "U")
        db.signup_user(1, "v", "V")
        db.create_post(1, "Original post")
        proc = ActionProcessor(db)
        result = proc.process(2, "repost", {"post_id": 1})
        assert result.success is True
        assert result.data["original_post_id"] == 1

    def test_quote_post(self, db):
        db.signup_user(0, "u", "U")
        db.create_post(1, "Original")
        proc = ActionProcessor(db)
        result = proc.process(1, "quote_post", {"post_id": 1, "content": "Adding my thoughts"})
        assert result.success is True

    def test_search_posts(self, populated_db):
        proc = ActionProcessor(populated_db)
        result = proc.process(1, "search_posts", {"query": "world"})
        assert result.success is True
        assert len(result.data["posts"]) >= 1

    def test_trend(self, populated_db):
        proc = ActionProcessor(populated_db)
        result = proc.process(1, "trend", {})
        assert result.success is True
        assert "posts" in result.data

    def test_traces_recorded(self, db):
        db.signup_user(0, "u", "U")
        proc = ActionProcessor(db)
        proc.process(1, "create_post", {"content": "trace test"})
        proc.process(1, "do_nothing", {})
        traces = db.get_all_traces()
        assert len(traces) == 2
        assert traces[0]["action"] == "create_post"
        assert traces[1]["action"] == "do_nothing"


class TestRecSys:
    def test_random_recs(self, populated_db):
        recsys = RecSys(populated_db, RecSysType.RANDOM, max_rec_posts=10)
        count = recsys.update_recommendations()
        assert count > 0
        recs = populated_db.get_recommended_posts(1)
        assert len(recs) > 0

    def test_reddit_hot_recs(self, populated_db):
        populated_db.like_post(2, 1)
        populated_db.like_post(3, 1)
        recsys = RecSys(populated_db, RecSysType.REDDIT, max_rec_posts=10)
        recsys.update_recommendations()
        recs = populated_db.get_recommended_posts(1)
        assert len(recs) > 0

    def test_twitter_recs(self, populated_db):
        recsys = RecSys(populated_db, RecSysType.TWITTER, max_rec_posts=10)
        recsys.update_recommendations()
        recs = populated_db.get_recommended_posts(1)
        assert len(recs) > 0

    def test_no_posts_no_recs(self, db):
        db.signup_user(0, "u", "U")
        recsys = RecSys(db, RecSysType.RANDOM, max_rec_posts=10)
        count = recsys.update_recommendations()
        assert count == 0


class TestPlatformState:
    def test_process_action(self):
        state = PlatformState(db_path=":memory:", recsys_type="random")
        state.db.signup_user(0, "u", "U")
        result = state.process_action(1, "create_post", {"content": "Hello"})
        assert result.success is True
        state.close()


class TestPlatformApi:
    def test_posts_and_threads_include_authors_and_comments(self):
        with TestClient(create_app()) as client:
            signup = client.post(
                "/signup/bulk",
                json={
                    "users": [
                        {"agent_id": 0, "user_name": "alice", "name": "Alice"},
                        {"agent_id": 1, "user_name": "bob", "name": "Bob"},
                    ]
                },
            )
            assert signup.status_code == 200

            post = client.post("/seed_post", json={"user_id": 1, "content": "hello from alice"})
            assert post.status_code == 200

            comment = client.post(
                "/action",
                json={
                    "user_id": 2,
                    "action_type": "create_comment",
                    "params": {"post_id": 1, "content": "reply from bob"},
                },
            )
            assert comment.status_code == 200
            assert comment.json()["success"] is True

            posts = client.get("/posts").json()
            assert posts[0]["author"] == "Alice"
            assert posts[0]["num_comments"] == 1

            threads = client.get("/threads").json()["threads"]
            assert threads[0]["author"] == "Alice"
            assert threads[0]["comments"][0]["author"] == "Bob"
            assert threads[0]["comments"][0]["content"] == "reply from bob"

    def test_advance_step(self):
        state = PlatformState(db_path=":memory:", recsys_type="random")
        state.db.signup_user(0, "u", "U")
        state.db.create_post(1, "Post")
        result = state.advance_step()
        assert result["time_step"] == 1
        assert result["recommendations_updated"] > 0
        state.close()

    def test_sequential_steps(self):
        state = PlatformState(db_path=":memory:", recsys_type="random")
        state.db.signup_user(0, "u", "U")
        state.db.create_post(1, "Post")
        state.advance_step()
        state.advance_step()
        state.advance_step()
        assert state.time_step == 3
        state.close()

    def test_full_simulation_cycle(self):
        state = PlatformState(db_path=":memory:", recsys_type="random")
        state.db.signup_user(0, "alice", "Alice", "tech")
        state.db.signup_user(1, "bob", "Bob", "finance")
        state.db.add_follow(1, 2)

        state.process_action(1, "create_post", {"content": "First post from Alice"})
        state.process_action(2, "create_post", {"content": "Bob's market update"})

        state.advance_step()

        result = state.process_action(1, "refresh", {})
        assert result.success is True

        state.process_action(1, "like_post", {"post_id": 2})
        state.process_action(2, "repost", {"post_id": 1})

        stats = state.db.stats()
        assert stats["post"] == 3
        assert stats["like"] == 1
        assert stats["trace"] >= 4

        state.close()
