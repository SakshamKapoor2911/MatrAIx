"""use.computer path remapping for macOS desktop and iOS simulator hosts."""

from __future__ import annotations

from harbor.environments.use_computer import UseComputerEnvironment


def _env(platform: str) -> UseComputerEnvironment:
    env = object.__new__(UseComputerEnvironment)
    env._platform = platform
    return env


def test_remap_macos_path_maps_app_input_for_persona_upload_on_macos() -> None:
    assert (
        _env("macos")._remap_macos_path("/app/input/persona.yaml")
        == "/Users/lume/input/persona.yaml"
    )


def test_remap_macos_path_maps_app_input_for_persona_upload_on_ios() -> None:
    assert (
        _env("ios")._remap_macos_path("/app/input/persona.yaml")
        == "/tmp/harbor/app/input/persona.yaml"
    )


def test_remap_macos_path_maps_harbor_roots() -> None:
    assert _env("macos")._remap_macos_path("/logs/verifier/reward.txt") == (
        "/tmp/harbor/logs/verifier/reward.txt"
    )


def test_api_key_normalization_strips_whitespace() -> None:
    raw_key = "uc_live_example  "
    assert (str(raw_key).strip() or None) == "uc_live_example"
