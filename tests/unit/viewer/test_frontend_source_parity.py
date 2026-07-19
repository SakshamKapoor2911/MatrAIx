from __future__ import annotations

import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[3]
VIEWER_APP = ROOT / "apps/viewer/app"


def test_viewer_lib_imports_resolve_to_checked_in_sources() -> None:
    lib_imports: set[str] = set()
    import_pattern = re.compile(r"""from\s+["']~/lib/([^"']+)["']""")

    for source_path in VIEWER_APP.rglob("*"):
        if source_path.suffix not in {".ts", ".tsx"}:
            continue
        text = source_path.read_text(encoding="utf-8")
        lib_imports.update(import_pattern.findall(text))

    assert lib_imports == {"api", "highlighter", "hooks", "types", "utils"}

    for module_name in sorted(lib_imports):
        candidates = [
            VIEWER_APP / "lib" / f"{module_name}.ts",
            VIEWER_APP / "lib" / f"{module_name}.tsx",
        ]
        assert any(candidate.is_file() for candidate in candidates), module_name
