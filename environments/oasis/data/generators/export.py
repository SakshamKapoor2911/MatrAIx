# export.py — Export generated profiles + network to OASIS-compatible CSV.
# Matches the exact format OASIS expects: user_id, name, username, description,
# user_char, following_agentid_list, previous_tweets, activity_level,
# activity_level_frequency, tweets_id.

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def export_twitter_csv(
    profiles: list[dict[str, Any]],
    following_lists: list[list[int]],
    output_path: str | Path,
    star_profiles: list[dict[str, Any]] | None = None,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_profiles = []
    if star_profiles:
        all_profiles.extend(star_profiles)
    all_profiles.extend(profiles)

    all_following = []
    if star_profiles:
        all_following.extend([[] for _ in star_profiles])
    all_following.extend(following_lists)

    fieldnames = [
        "user_id", "name", "username", "description", "user_char",
        "following_agentid_list", "previous_tweets", "activity_level",
        "activity_level_frequency", "tweets_id",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, profile in enumerate(all_profiles):
            following = all_following[i] if i < len(all_following) else []
            row = {
                "user_id": i,
                "name": profile.get("realname", profile.get("name", f"User_{i}")),
                "username": profile.get("username", f"user_{i}"),
                "description": profile.get("bio", ""),
                "user_char": profile.get("persona", profile.get("user_char", "")),
                "following_agentid_list": repr(following),
                "previous_tweets": repr(profile.get("previous_tweets", [])),
                "activity_level": repr(["active"] * 24),
                "activity_level_frequency": repr([100] * 24),
                "tweets_id": str(profile.get("tweets_id", 0)),
            }
            writer.writerow(row)

    return output_path


def export_reddit_json(
    profiles: list[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    import json
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)

    return output_path
