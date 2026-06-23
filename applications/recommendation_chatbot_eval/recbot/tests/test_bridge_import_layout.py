from __future__ import annotations

import importlib.util
from pathlib import Path, PosixPath
from unittest.mock import patch


def test_interecagent_bridge_imports_from_root_level_app_layout():
    module_path = Path(__file__).resolve().parents[1] / "interecagent_bridge.py"
    spec = importlib.util.spec_from_file_location(
        "recbot_bridge_root_level_import_test",
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)

    with patch.object(
        Path,
        "resolve",
        return_value=PosixPath("/app/recbot/interecagent_bridge.py"),
    ):
        spec.loader.exec_module(module)
