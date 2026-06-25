import json
import zipfile
from pathlib import Path

import pytest

from scripts.setup_recai_resources import setup_resources


def _make_domain_zip(zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w") as zf:
        for domain, info in {"game": "games.ftr", "movie": "movies.ftr",
                             "beauty_product": "products.ftr"}.items():
            settings = {
                "GAME_INFO_FILE": info,
                "TABLE_COL_DESC_FILE": "columns.json",
                "MODEL_CKPT_FILE": "SASRec-SASRec.pth",
                "ITEM_SIM_FILE": "item_sim.npy",
                "USE_COLS": ["id", "title"],
                "CATEGORICAL_COLS": ["tags"],
            }
            zf.writestr(f"{domain}/settings.json", json.dumps(settings))
            zf.writestr(f"{domain}/columns.json", "{}")
            zf.writestr(f"{domain}/{info}", "x")
            zf.writestr(f"{domain}/SASRec-SASRec.pth", "x")
            zf.writestr(f"{domain}/item_sim.npy", "x")


def test_setup_extracts_and_verifies_all_domains(tmp_path: Path):
    zip_path = tmp_path / "all_resources.zip"
    _make_domain_zip(zip_path)
    dest = tmp_path / "resources"

    domains = setup_resources(zip_path, dest)

    assert sorted(domains) == ["beauty_product", "game", "movie"]
    assert (dest / "game" / "settings.json").exists()
    assert (dest / "movie" / "movies.ftr").exists()


def test_setup_raises_when_referenced_file_missing(tmp_path: Path):
    zip_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("game/settings.json", json.dumps({
            "GAME_INFO_FILE": "games.ftr", "TABLE_COL_DESC_FILE": "columns.json",
            "MODEL_CKPT_FILE": "SASRec-SASRec.pth", "ITEM_SIM_FILE": "item_sim.npy",
            "USE_COLS": [], "CATEGORICAL_COLS": [],
        }))
        # intentionally omit the referenced data files
    with pytest.raises(RuntimeError):
        setup_resources(zip_path, tmp_path / "out")
