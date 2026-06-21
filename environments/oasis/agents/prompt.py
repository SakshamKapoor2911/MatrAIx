# prompt.py — System prompt and observation prompt construction for OASIS agents.
# Matches OASIS's UserInfo.to_system_message() + SocialEnvironment.to_text_prompt().
# The system prompt carries persona identity; the observation prompt carries the feed state.

from __future__ import annotations

from typing import Any

from environments.oasis.persona_loader.adapter import OasisUserInfo


SYSTEM_PROMPT_TEMPLATE = """You are a social media user. Your actions must be consistent with your personality and profile described below.

# WHO YOU ARE
Name: {name}
{user_profile}

# OBJECTIVE
You will be shown posts from your social media feed. After reviewing them, choose ONE action that reflects your personality, interests, and current mood.

# RESPONSE FORMAT
You MUST respond with ONLY a JSON object choosing one action. No explanation, no thinking tags, just the JSON.

Available actions:
- {{"name": "create_post", "arguments": {{"content": "your post text"}}}}
- {{"name": "like_post", "arguments": {{"post_id": <integer>}}}}
- {{"name": "repost", "arguments": {{"post_id": <integer>}}}}
- {{"name": "follow", "arguments": {{"user_id": <integer>}}}}
- {{"name": "do_nothing", "arguments": {{}}}}

Respond with ONLY the JSON object."""


OBSERVATION_TEMPLATE = """Your feed (step {step}):
{feed_text}

Pick ONE action that best reflects your personality right now. Consider: creating an original post about your field, liking a post you agree with, reposting something worth sharing, following an interesting user, or doing nothing if nothing catches your eye. Vary your behavior naturally.

Respond with JSON only. /no_think"""


def build_system_prompt(persona: OasisUserInfo) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        name=persona.name,
        user_profile=persona.user_profile,
    )


def build_observation_prompt(posts: list[dict[str, Any]], max_posts: int = 20, step: int = 1) -> str:
    if not posts:
        feed_text = "Your feed is empty. No posts to see right now. You may want to create a post or search for content."
        return OBSERVATION_TEMPLATE.format(feed_text=feed_text, step=step)

    display_posts = posts[:max_posts]
    lines = []
    for post in display_posts:
        post_id = post.get("post_id", "?")
        user_id = post.get("user_id", "?")
        content = post.get("content", "")
        likes = post.get("num_likes", 0)
        dislikes = post.get("num_dislikes", 0)
        comments = post.get("num_comments", 0)
        shares = post.get("num_shares", 0)

        line = (
            f"[Post #{post_id} by user {user_id}] "
            f"{content} "
            f"(likes: {likes}, dislikes: {dislikes}, comments: {comments}, reposts: {shares})"
        )
        lines.append(line)

    feed_text = "\n".join(lines)
    return OBSERVATION_TEMPLATE.format(feed_text=feed_text, step=step)
