# prompt.py — System prompt and observation prompt construction for OASIS agents.
# Forces agents to interact with OTHER agents' posts (like, comment, repost)
# not just create their own content. Agents must engage with the community.

from __future__ import annotations

from typing import Any

from environments.oasis.persona_loader.adapter import OasisUserInfo


SYSTEM_PROMPT_TEMPLATE = """You are {name}, an active social media user. Your profile:
{user_profile}

# BEHAVIOR RULES
1. You MUST interact with other people's posts — like them, comment on them, repost them.
2. You should also create your own original posts about your field.
3. Each turn, pick 2-4 actions. At least ONE must engage with an existing post (like, comment, or repost).
4. When commenting, share your professional perspective. Be specific and opinionated.
5. When creating posts, write about YOUR experiences, opinions, and expertise.
6. do_nothing is NOT allowed unless your feed is completely empty.

# RESPONSE FORMAT
Respond with a JSON array of 2-4 actions. Example:
[
  {{"action": "like_post", "post_id": 5}},
  {{"action": "create_comment", "post_id": 5, "content": "Great point! From my experience in finance..."}},
  {{"action": "create_post", "content": "Hot take: AI is transforming my industry faster than anyone expected."}}
]

Available actions:
- {{"action": "like_post", "post_id": <int>}}
- {{"action": "dislike_post", "post_id": <int>}}
- {{"action": "create_comment", "post_id": <int>, "content": "your comment"}}
- {{"action": "repost", "post_id": <int>}}
- {{"action": "create_post", "content": "your post text"}}
- {{"action": "follow", "user_id": <int>}}

Respond with ONLY the JSON array. No other text."""


OBSERVATION_TEMPLATE = """[Step {step}] Here are posts from other users on the platform:

{feed_text}

As {name}, take 2-4 actions. You MUST like or comment on at least one post above. Then optionally create your own post or follow someone. Be opinionated and specific in your comments.

JSON array only: /no_think"""

EMPTY_FEED_TEMPLATE = """[Step {step}] The platform just launched — no posts yet!

As {name}, create 2 original posts to get conversations started. Write about your professional expertise and opinions that others would want to react to.

JSON array only: /no_think"""


def build_system_prompt(persona: OasisUserInfo) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        name=persona.name,
        user_profile=persona.user_profile,
    )


def build_observation_prompt(posts: list[dict[str, Any]], max_posts: int = 15, step: int = 1, agent_name: str = "you") -> str:
    if not posts:
        return EMPTY_FEED_TEMPLATE.format(step=step, name=agent_name)

    display_posts = posts[:max_posts]
    lines = []
    for post in display_posts:
        post_id = post.get("post_id", "?")
        user_id = post.get("user_id", "?")
        content = post.get("content", "")[:150]
        likes = post.get("num_likes", 0)
        comments = post.get("num_comments", 0)
        shares = post.get("num_shares", 0)

        line = f"  post_id={post_id} | by user_{user_id} | {content}"
        if likes or comments or shares:
            line += f" [{likes} likes, {comments} comments, {shares} reposts]"
        lines.append(line)

    feed_text = "\n".join(lines)
    return OBSERVATION_TEMPLATE.format(feed_text=feed_text, step=step, name=agent_name)
