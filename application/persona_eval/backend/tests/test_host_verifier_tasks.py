"""Host-native Harbor tasks must write verifier rewards via HARBOR_VERIFIER_DIR."""

from backend.service.example_task_catalog import repo_root

_HOST_NATIVE_VERIFIER_SCRIPTS = (
    "application/tasks/persona-survey/tests/test.sh",
    "application/tasks/recommender-agent_chat_api/tests/test.sh",
)


def test_host_native_verifier_scripts_use_harbor_verifier_dir():
    root = repo_root()
    for relative in _HOST_NATIVE_VERIFIER_SCRIPTS:
        content = (root / relative).read_text(encoding="utf-8")
        assert "HARBOR_VERIFIER_DIR" in content, relative
        assert "echo 1 > /logs/verifier/reward.txt" not in content, relative
        assert "echo 0 > /logs/verifier/reward.txt" not in content, relative
