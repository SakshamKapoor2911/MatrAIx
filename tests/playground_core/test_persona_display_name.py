from matraix.persona_display_name import synthetic_display_name


def test_synthetic_display_name_is_stable():
    dims = {"region": "East Asia"}
    assert synthetic_display_name("0042", dims) == synthetic_display_name("0042", dims)


def test_synthetic_display_name_uses_region_pool():
    east = synthetic_display_name("0001", {"region": "East Asia"})
    west = synthetic_display_name("0001", {"region": "Western Europe"})
    assert east != west
    assert " " in east
    assert " " in west


def test_synthetic_display_name_fallback_without_region():
    name = synthetic_display_name("0099", {})
    assert name.count(" ") == 1
