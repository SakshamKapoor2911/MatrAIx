import csv
import json
from pathlib import Path


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_rank_users_scores_reviewers_by_rich_persona_signals():
    from persona.curation.existing_data.scripts.select_amazon_top_reviewers import (
        rank_users,
    )

    rows = [
        {
            "user_id": "USER_LOW",
            "review_count": 40,
            "text_reviews": 40,
            "text_chars": 4_000,
            "category_count": 4,
            "history_days": 300,
            "verified_share": 0.8,
        },
        {
            "user_id": "USER_HIGH",
            "review_count": 120,
            "text_reviews": 110,
            "text_chars": 20_000,
            "category_count": 14,
            "first_date": "2018-01-01",
            "last_date": "2023-01-01",
            "verified_share": 0.95,
            "categories": ["Books", "Electronics"],
        },
        {
            "user_id": "USER_MEDIUM",
            "review_count": 80,
            "text_reviews": 0,
            "text_chars": 12_000,
            "category_count": 8,
            "history_days": 900,
            "verified_share": 0.9,
        },
    ]

    ranked = rank_users(rows, top_k=2)

    assert [row["user_id"] for row in ranked] == ["USER_HIGH", "USER_MEDIUM"]
    assert [row["rank"] for row in ranked] == [1, 2]
    assert ranked[0]["history_days"] > 1_800
    assert ranked[1]["text_reviews"] == 80
    assert ranked[0]["chars_per_text_review"] == round(20_000 / 110, 3)
    assert ranked[0]["rich_persona_score"] > ranked[1]["rich_persona_score"]


def test_write_outputs_creates_reviewer_queue_artifacts(tmp_path: Path):
    from persona.curation.existing_data.scripts.select_amazon_top_reviewers import (
        write_outputs,
    )

    selected = [
        {
            "rank": 1,
            "user_id": "USER_HIGH",
            "user_bucket": "aa",
            "rich_persona_score": 0.98,
            "review_count": 120,
            "text_reviews": 110,
            "text_chars": 20_000,
            "chars_per_text_review": 181.818,
            "category_count": 14,
            "history_days": 1_826,
            "history_years": 5.0,
            "verified_share": 0.95,
            "verified_count": 114,
            "rating_count": 120,
            "average_rating": 4.4,
            "first_date": "2018-01-01",
            "last_date": "2023-01-01",
            "categories": ["Books", "Electronics"],
        }
    ]

    summary = write_outputs(
        selected,
        source_count=3,
        output_dir=tmp_path,
        repo_id="Example/Repo",
        artifact="amazon/modal_artifacts/example",
    )

    stem = "amazon_top_00001_rich_persona_reviewers_2018_2023"
    assert summary["selected_rows"] == 1
    assert (tmp_path / f"{stem}.jsonl").exists()
    assert (tmp_path / f"{stem}.csv").exists()
    assert (tmp_path / "amazon_top_00001_rich_persona_reviewer_ids_2018_2023.txt").read_text(
        encoding="utf-8"
    ) == "USER_HIGH\n"

    rows = _read_jsonl(tmp_path / f"{stem}.jsonl")
    assert rows[0]["categories"] == ["Books", "Electronics"]

    with (tmp_path / f"{stem}.csv").open(encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert csv_rows[0]["categories"] == "Books|Electronics"

    markdown = (tmp_path / f"{stem}.md").read_text(encoding="utf-8")
    assert "Amazon Top 1 Rich Persona Reviewers" in markdown
    assert "Example/Repo" in markdown
