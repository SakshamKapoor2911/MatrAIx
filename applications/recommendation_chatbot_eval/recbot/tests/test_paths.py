from recbot.paths import APP_ROOT, default_interecagent_root


def test_default_root_points_at_in_repo_submodule():
    root = default_interecagent_root()
    assert root == APP_ROOT / "recai" / "InteRecAgent"
    assert root.name == "InteRecAgent"
    assert root.parent.name == "recai"


def test_app_root_is_the_eval_package_dir():
    assert APP_ROOT.name == "recommendation_chatbot_eval"
