"""Public naming contract for PersonaEval."""

from __future__ import annotations

from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]
FORMER_BRAND = "RecBot" + " Studio"


def test_public_product_name_is_persona_eval(client):
    """The public app/API brand should be PersonaEval."""
    assert client.app.title == "PersonaEval API"


def test_frontend_header_uses_persona_eval_brand():
    top_bar = (APP_ROOT / "frontend/src/components/TopBar.tsx").read_text()

    assert "PersonaEval" in top_bar
    assert FORMER_BRAND not in top_bar


def test_public_docs_do_not_use_old_studio_name():
    public_files = [
        APP_ROOT / "README.md",
        APP_ROOT / "run_demo.sh",
        APP_ROOT / "backend/api/app.py",
        APP_ROOT / "backend/run_dev.sh",
        APP_ROOT / "backend/run_real.sh",
        APP_ROOT / "frontend/index.html",
        APP_ROOT / "frontend/package.json",
        APP_ROOT / "frontend/src/App.tsx",
        APP_ROOT / "frontend/src/components/ErrorBoundary.tsx",
        APP_ROOT / "frontend/src/lib/api.ts",
        APP_ROOT / "frontend/src/lib/types.ts",
    ]

    for path in public_files:
        assert FORMER_BRAND not in path.read_text(), str(path.relative_to(APP_ROOT))
