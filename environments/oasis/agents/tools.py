# tools.py — OpenAI function-calling tool definitions matching OASIS's 22 core actions.
# These schemas are sent to the LLM so it can select actions via structured tool_calls.
# Maps 1:1 with the platform's ActionType enum and /action endpoint contract.

from __future__ import annotations

from typing import Any


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "create_post",
            "description": "Create a new post on the social media platform. Use this to share your thoughts, opinions, or reactions to what you've seen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The text content of the post you want to publish."}
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "like_post",
            "description": "Like a post to show approval or agreement with its content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "post_id": {"type": "integer", "description": "The ID of the post to like."}
                },
                "required": ["post_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "unlike_post",
            "description": "Remove your like from a previously liked post.",
            "parameters": {
                "type": "object",
                "properties": {
                    "post_id": {"type": "integer", "description": "The ID of the post to unlike."}
                },
                "required": ["post_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dislike_post",
            "description": "Dislike a post to show disapproval or disagreement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "post_id": {"type": "integer", "description": "The ID of the post to dislike."}
                },
                "required": ["post_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "undo_dislike_post",
            "description": "Remove your dislike from a previously disliked post.",
            "parameters": {
                "type": "object",
                "properties": {
                    "post_id": {"type": "integer", "description": "The ID of the post to undo dislike."}
                },
                "required": ["post_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "repost",
            "description": "Share an existing post to your followers. Use when you want to amplify content without adding commentary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "post_id": {"type": "integer", "description": "The ID of the post to repost."}
                },
                "required": ["post_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "quote_post",
            "description": "Share an existing post with your own commentary added. Use when you want to repost but add your own perspective.",
            "parameters": {
                "type": "object",
                "properties": {
                    "post_id": {"type": "integer", "description": "The ID of the post to quote."},
                    "content": {"type": "string", "description": "Your commentary on the quoted post."},
                },
                "required": ["post_id", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_comment",
            "description": "Write a comment on a post. Use to reply, ask questions, or engage in discussion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "post_id": {"type": "integer", "description": "The ID of the post to comment on."},
                    "content": {"type": "string", "description": "Your comment text."},
                },
                "required": ["post_id", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "like_comment",
            "description": "Like a comment to show agreement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "comment_id": {"type": "integer", "description": "The ID of the comment to like."}
                },
                "required": ["comment_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dislike_comment",
            "description": "Dislike a comment to show disagreement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "comment_id": {"type": "integer", "description": "The ID of the comment to dislike."}
                },
                "required": ["comment_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "follow",
            "description": "Follow a user to see their posts in your feed. Follow users whose content interests you.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "The user ID of the person to follow."}
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "unfollow",
            "description": "Unfollow a user to stop seeing their posts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "The user ID of the person to unfollow."}
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mute",
            "description": "Mute a user so their posts no longer appear in your feed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "The user ID to mute."}
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "unmute",
            "description": "Unmute a previously muted user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "The user ID to unmute."}
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_posts",
            "description": "Search for posts containing specific keywords or topics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_user",
            "description": "Search for a user by name or username.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The user name or username to search for."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trend",
            "description": "View trending posts on the platform. See what's popular right now.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "report_post",
            "description": "Report a post for violating platform rules.",
            "parameters": {
                "type": "object",
                "properties": {
                    "post_id": {"type": "integer", "description": "The ID of the post to report."},
                    "reason": {"type": "string", "description": "Reason for reporting."},
                },
                "required": ["post_id", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "do_nothing",
            "description": "Choose to take no action this turn. Use when nothing in your feed interests you or you prefer to just observe.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

TOOL_NAMES: list[str] = [t["function"]["name"] for t in TOOL_DEFINITIONS]

DEFAULT_TWITTER_ACTIONS: list[str] = [
    "create_post", "like_post", "repost", "follow", "do_nothing", "quote_post",
]

DEFAULT_REDDIT_ACTIONS: list[str] = [
    "like_post", "dislike_post", "create_post", "create_comment",
    "like_comment", "dislike_comment", "search_posts", "search_user",
    "trend", "do_nothing", "follow", "mute",
]


def get_tools_for_actions(available_actions: list[str] | None = None) -> list[dict[str, Any]]:
    if available_actions is None:
        return TOOL_DEFINITIONS
    return [t for t in TOOL_DEFINITIONS if t["function"]["name"] in available_actions]
