from __future__ import annotations

from pathlib import Path

from harbor.telemetry.ios_probe import (
    device_name_matches,
    device_record_matches,
    merge_watched_app_records,
    normalize_match_token,
    parse_plutil_section_text,
    runtime_key_matches,
    section_info_candidates,
    select_booted_device,
    simulator_data_root_from_container_path,
)


def test_normalize_match_token_collapses_ios_runtime_variants() -> None:
    assert normalize_match_token("com.apple.CoreSimulator.SimRuntime.iOS-26-4") == "ios264"
    assert normalize_match_token("iOS 26.4") == "ios264"
    assert normalize_match_token("iPhone-17") == "iphone17"


def test_device_name_matches_iphone_variants() -> None:
    hint = "com.apple.CoreSimulator.SimDeviceType.iPhone-17"
    assert device_name_matches("iPhone 17", hint)
    assert device_name_matches("iPhone 17 Pro", hint)
    assert not device_name_matches("iPhone 15", hint)


def test_runtime_key_matches_dotted_and_dashed_keys() -> None:
    hint = "com.apple.CoreSimulator.SimRuntime.iOS-26-4"
    assert runtime_key_matches("com.apple.CoreSimulator.SimRuntime.iOS-26-4", hint)
    assert runtime_key_matches("iOS 26.4", hint)
    assert not runtime_key_matches("iOS 18.0", hint)


def test_select_booted_device_prefers_hint_match() -> None:
    devices = {
        "iOS 26.4": [
            {"state": "Booted", "name": "iPhone 17", "udid": "A"},
            {"state": "Shutdown", "name": "iPhone 15", "udid": "B"},
        ],
        "iOS 18.0": [
            {"state": "Booted", "name": "iPhone 15", "udid": "C"},
        ],
    }
    device, meta = select_booted_device(
        devices,
        device_type_hint="iPhone-17",
        runtime_hint="iOS-26-4",
    )
    assert device is not None
    assert device["udid"] == "A"
    assert meta == {}


def test_select_booted_device_falls_back_to_any_booted() -> None:
    devices = {
        "iOS 18.0": [
            {"state": "Booted", "name": "iPhone 15 Pro", "udid": "C"},
        ],
    }
    device, meta = select_booted_device(
        devices,
        device_type_hint="iPhone-17",
        runtime_hint="iOS-26-4",
    )
    assert device is not None
    assert device["udid"] == "C"
    assert meta.get("hint_fallback") is True


def test_device_record_matches_sim_device_type_identifier() -> None:
    device = {
        "name": "sim-fac49b5e4160",
        "deviceTypeIdentifier": "com.apple.CoreSimulator.SimDeviceType.iPhone-17",
    }
    hint = "com.apple.CoreSimulator.SimDeviceType.iPhone-17"
    assert device_record_matches(device, hint)


def test_simulator_data_root_from_container_path() -> None:
    container = (
        "/Users/lume/Library/Developer/CoreSimulator/Devices/"
        "ABC/data/Containers/Data/Application/1234/Documents"
    )
    root = simulator_data_root_from_container_path(container, "ABC")
    assert root == Path(
        "/Users/lume/Library/Developer/CoreSimulator/Devices/ABC/data"
    )


def test_section_info_candidates_include_versioned_and_mobile_mirror() -> None:
    data_root = Path("/tmp/sim/data")
    paths = section_info_candidates(data_root)
    joined = "\n".join(path.as_posix() for path in paths)
    assert "VersionedSectionInfo.plist" in joined
    assert "SectionInfo.plist" in joined
    assert "private/var/mobile" in joined


def test_parse_plutil_section_text_extracts_messages_status() -> None:
    sample = '''
    "com.apple.MobileSMS" => {
      "authorizationStatus" => 2
      "allowsNotifications" => true
    }
    '''
    parsed = parse_plutil_section_text(sample, ["com.apple.MobileSMS"])
    assert parsed["com.apple.MobileSMS"]["authorization_status"] == 2
    assert parsed["com.apple.MobileSMS"]["notifications_enabled"] is True
    assert parsed["com.apple.MobileSMS"]["allows_notifications"] is True


def test_merge_watched_app_records_combines_sources() -> None:
    merged = merge_watched_app_records(
        {"com.apple.MobileSMS": {"source": "spawn_plutil", "authorization_status": 2}},
        {"com.apple.MobileSMS": {"display_name": "Messages"}},
    )
    assert merged["com.apple.MobileSMS"]["source"] == "spawn_plutil"
    assert merged["com.apple.MobileSMS"]["display_name"] == "Messages"
