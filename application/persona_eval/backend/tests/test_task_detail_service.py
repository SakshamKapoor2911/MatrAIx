"""Tests for task detail loading."""

from __future__ import annotations

from backend.service.task_detail_service import get_task_detail


def test_get_task_detail_reads_instruction_markdown(tmp_path):
    task_dir = tmp_path / "application" / "tasks" / "example-chat-api_demo"
    task_dir.mkdir(parents=True)
    (task_dir / "task.toml").write_text(
        "[metadata]\ntype = \"chat\"\n[task]\nname = \"demo/chat\"\n",
        encoding="utf-8",
    )
    (task_dir / "instruction.md").write_text(
        "# Demo Chat Task\n\nTalk to the sidecar naturally.\n\n## Steps\n\n1. Say hi.\n",
        encoding="utf-8",
    )
    detail = get_task_detail("application/tasks/example-chat-api_demo", repo_root=tmp_path)
    assert detail["title"] == "Demo Chat Task"
    assert "Talk to the sidecar" in detail["description"]
    assert "Say hi" in detail["profileMarkdown"]
    assert detail["metaType"] == "chat"
