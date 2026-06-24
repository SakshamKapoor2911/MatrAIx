#!/usr/bin/env python3
"""Local web demo for offline wiki collaboration.

This module intentionally uses only the Python standard library plus the
existing collaboration primitives in this repository. It serves a small local
operator console that can create an assignment package, run it through the real
range runner, copy the returned archive into a receiver inbox, audit it, and
merge accepted rows.
"""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import gzip
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import shlex
import shutil
import sqlite3
import sys
import tarfile
import time
from typing import Any
from urllib.parse import unquote, urlparse

from personas.existing_data_curation.scripts.audit_wiki_results import audit_archives
from personas.existing_data_curation.scripts.merge_wiki_results import merge_archives
from personas.existing_data_curation.wiki_collab.core import (
    Assignment,
    compute_input_sha256,
    load_jsonl,
    load_protocol_manifest,
    profile_input_payload,
    safe_name,
    sha256_file,
)
from personas.existing_data_curation.worker_kit.run_range import render_prompt, run_range


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROTOCOL_DIR = (
    REPO_ROOT / "personas/existing_data_curation/protocols/persona_attribution_v1"
)
DEFAULT_DEMO_ROOT = (
    REPO_ROOT / "personas/existing_data_curation/wiki_collab/site_runtime"
)
DEFAULT_DERIVATIVES_DIR = Path(
    os.environ.get(
        "MATRAIX_WIKI_DERIVATIVES_DIR",
        "/data2/zonglin/wiki_dumps/enwiki/20260601/person_text_derivatives",
    )
)
CLAUDE_WRAPPER = Path(__file__).resolve().with_name("claude_json_backend.py")


DEMO_PROFILES: list[dict[str, Any]] = [
    {
        "page_id": 307,
        "qid": "Q91",
        "title": "Abraham Lincoln",
        "entity_type": "real_person",
        "tags": ["real_person"],
        "source_url": "https://en.wikipedia.org/wiki/Abraham_Lincoln",
        "revision_id": 1357045394,
        "revision_timestamp": "2026-05-31T12:26:21Z",
        "profile_text": (
            "Abraham Lincoln (February 12, 1809 - April 15, 1865) was the 16th "
            "president of the United States, serving from 1861 until his assassination "
            "in 1865. He led the United States through the American Civil War, defeating "
            "the Confederacy and playing a major role in the abolition of slavery.\n\n"
            "Born in a one-room log cabin in Kentucky, Lincoln was raised on the frontier. "
            "He was self-educated and became a lawyer, Illinois state legislator, and U.S. "
            "representative. Angered by the Kansas-Nebraska Act of 1854, he became a "
            "leader of the new Republican Party."
        ),
        "sections": [
            {
                "heading": "Lead",
                "level": 0,
                "char_count": 2415,
                "text": "Abraham Lincoln was the 16th president of the United States and led the country through the American Civil War.",
            },
            {
                "heading": "Early life",
                "level": 3,
                "char_count": 2019,
                "text": "Born in a one-room log cabin in Kentucky, Lincoln was raised on the frontier and was largely self-educated.",
            },
        ],
        "chunks": [
            {
                "chunk_id": "Q91::lead::000",
                "section_heading": "Lead",
                "char_count": 1939,
                "text": "Abraham Lincoln was the 16th president of the United States, serving from 1861 until his assassination in 1865.",
            },
            {
                "chunk_id": "Q91::early_life::000",
                "section_heading": "Early life",
                "char_count": 1579,
                "text": "Born in a one-room log cabin in Kentucky, Lincoln was raised on Sinking Spring Farm near Hodgenville.",
            },
        ],
    },
    {
        "page_id": 305,
        "qid": "Q41746",
        "title": "Achilles",
        "entity_type": "fictional_character",
        "tags": ["fictional_character"],
        "source_url": "https://en.wikipedia.org/wiki/Achilles",
        "revision_id": 1353756424,
        "revision_timestamp": "2026-05-12T04:37:36Z",
        "profile_text": (
            "In Greek mythology, Achilles or Achilleus was a hero of the Trojan War who "
            "was known as being the greatest of all the Greek warriors. The central "
            "character in Homer's Iliad, he was the son of the Nereid Thetis and Peleus, "
            "king of Phthia and famous Argonaut. Achilles was raised in Phthia along "
            "with his childhood companion Patroclus and received his education by Chiron."
        ),
        "sections": [
            {
                "heading": "Lead",
                "level": 0,
                "char_count": 1396,
                "text": "Achilles was a hero of the Trojan War and a central character in Homer's Iliad.",
            },
            {
                "heading": "Etymology",
                "level": 2,
                "char_count": 1824,
                "text": "Linear B tablets attest to the personal name Achilleus in early forms.",
            },
        ],
        "chunks": [
            {
                "chunk_id": "Q41746::lead::000",
                "section_heading": "Lead",
                "char_count": 1396,
                "text": "Achilles was known as the greatest of all the Greek warriors in the Trojan War.",
            }
        ],
    },
    {
        "page_id": 308,
        "qid": "Q868",
        "title": "Aristotle",
        "entity_type": "real_person",
        "tags": ["real_person"],
        "source_url": "https://en.wikipedia.org/wiki/Aristotle",
        "revision_id": 1356624517,
        "revision_timestamp": "2026-05-28T22:04:41Z",
        "profile_text": (
            "Aristotle (384-322 BC) was an ancient Greek philosopher and polymath. His "
            "writings span the natural sciences, philosophy, linguistics, economics, "
            "politics, psychology, and the arts. As the founder of the Peripatetic school "
            "of philosophy in the Lyceum in Athens, he began the wider Aristotelian "
            "tradition that followed."
        ),
        "sections": [
            {
                "heading": "Lead",
                "level": 0,
                "char_count": 2419,
                "text": "Aristotle was an ancient Greek philosopher and polymath whose writings span many fields.",
            },
            {
                "heading": "Life",
                "level": 2,
                "char_count": 7024,
                "text": "Aristotle was born in 384 BC in Stagira and later joined Plato's Academy in Athens.",
            },
        ],
        "chunks": [
            {
                "chunk_id": "Q868::lead::000",
                "section_heading": "Lead",
                "char_count": 1401,
                "text": "Aristotle's writings span the natural sciences, philosophy, linguistics, economics, politics, psychology, and the arts.",
            }
        ],
    },
    {
        "page_id": 339,
        "qid": "Q132524",
        "title": "Ayn Rand",
        "entity_type": "real_person",
        "tags": ["real_person"],
        "source_url": "https://en.wikipedia.org/wiki/Ayn_Rand",
        "revision_id": 1356299287,
        "revision_timestamp": "2026-05-26T23:19:40Z",
        "profile_text": (
            "Alice O'Connor, better known by her pen name Ayn Rand, was a Russian-American "
            "writer and philosopher. She is known for her fiction and for developing a "
            "philosophical system which she named Objectivism. Born and educated in Russia, "
            "she moved to the United States in 1926."
        ),
        "sections": [
            {
                "heading": "Lead",
                "level": 0,
                "char_count": 1950,
                "text": "Ayn Rand was a Russian-American writer and philosopher known for fiction and Objectivism.",
            },
            {
                "heading": "Early life",
                "level": 3,
                "char_count": 2642,
                "text": "Rand was born Alisa Zinovyevna Rosenbaum in Saint Petersburg.",
            },
        ],
        "chunks": [
            {
                "chunk_id": "Q132524::lead::000",
                "section_heading": "Lead",
                "char_count": 1950,
                "text": "Ayn Rand was a Russian-American writer and philosopher known for developing Objectivism.",
            }
        ],
    },
]


LINCOLN_FULL_ARTICLE_FOOTPRINT: dict[str, Any] = {
    "title": "Abraham Lincoln",
    "page_id": 307,
    "qid": "Q91",
    "source_url": "https://en.wikipedia.org/wiki/Abraham_Lincoln",
    "api_url": "",
    "source_dump": "enwiki-20260601",
    "revision_id": 1357045394,
    "revision_timestamp": "2026-05-31T12:26:21Z",
    "wikitext_chars": 159_311,
    "plain_text_chars": 74_335,
    "section_count": 34,
    "chunk_count": 56,
    "media_refs": 17,
    "derive_params": {
        "chunk_size": 2000,
        "chunk_overlap": 200,
        "min_section_chars": 80,
        "min_chunk_chars": 120,
    },
    "sections": [
        {"heading": "Lead", "level": 0, "char_count": 2415},
        {"heading": "Early life", "level": 3, "char_count": 2019},
        {"heading": "Education and move to Illinois", "level": 3, "char_count": 1279},
        {"heading": "Marriage and children", "level": 3, "char_count": 2245},
        {"heading": "Early vocations and militia service", "level": 3, "char_count": 2013},
        {"heading": "Illinois state legislature (1834-1842)", "level": 3, "char_count": 1607},
        {"heading": "U.S. House of Representatives (1847-1849)", "level": 3, "char_count": 2395},
        {"heading": "Prairie lawyer", "level": 3, "char_count": 2310},
        {"heading": "Emergence as Republican leader", "level": 3, "char_count": 2456},
        {"heading": "1856 campaign", "level": 4, "char_count": 984},
        {"heading": "Dred Scott v. Sandford", "level": 4, "char_count": 983},
        {"heading": "Lincoln-Douglas debates and Cooper Union speech", "level": 3, "char_count": 3624},
        {"heading": "1860 presidential election", "level": 3, "char_count": 2651},
        {"heading": "Secession and inauguration", "level": 4, "char_count": 3148},
        {"heading": "Personnel", "level": 4, "char_count": 1491},
        {"heading": "Commander-in-Chief", "level": 4, "char_count": 2307},
        {"heading": "Early Union military strategy", "level": 4, "char_count": 3662},
        {"heading": "McClellan", "level": 4, "char_count": 2971},
        {"heading": "Emancipation Proclamation", "level": 4, "char_count": 2625},
        {"heading": "Gettysburg Address (1863)", "level": 4, "char_count": 829},
        {"heading": "Promoting Grant", "level": 4, "char_count": 1652},
        {"heading": "Fiscal and monetary policy", "level": 4, "char_count": 4537},
        {"heading": "Foreign policy", "level": 4, "char_count": 2254},
        {"heading": "Native Americans", "level": 4, "char_count": 2226},
        {"heading": "Second term", "level": 3, "char_count": 159},
        {"heading": "Re-election", "level": 4, "char_count": 1970},
        {"heading": "Reconstruction", "level": 4, "char_count": 4097},
        {"heading": "Assassination", "level": 2, "char_count": 1820},
        {"heading": "Funeral and burial", "level": 3, "char_count": 841},
        {"heading": "Philosophy and views", "level": 2, "char_count": 1717},
        {"heading": "Religious views", "level": 3, "char_count": 1918},
        {"heading": "Health and appearance", "level": 2, "char_count": 1828},
        {"heading": "Historical reputation", "level": 3, "char_count": 3604},
        {"heading": "Memorials and commemorations", "level": 3, "char_count": 1632},
    ],
    "chunk_preview": [
        {"chunk_id": "Q91::lead::000", "section_heading": "Lead", "char_count": 1939},
        {"chunk_id": "Q91::lead::001", "section_heading": "Lead", "char_count": 675},
        {"chunk_id": "Q91::early_life::000", "section_heading": "Early life", "char_count": 1579},
        {"chunk_id": "Q91::early_life::001", "section_heading": "Early life", "char_count": 640},
        {
            "chunk_id": "Q91::education_and_move_to_illinois::000",
            "section_heading": "Education and move to Illinois",
            "char_count": 1279,
        },
        {"chunk_id": "Q91::marriage_and_children::000", "section_heading": "Marriage and children", "char_count": 1534},
        {"chunk_id": "Q91::marriage_and_children::001", "section_heading": "Marriage and children", "char_count": 911},
        {
            "chunk_id": "Q91::early_vocations_and_militia_service::000",
            "section_heading": "Early vocations and militia service",
            "char_count": 1492,
        },
        {
            "chunk_id": "Q91::early_vocations_and_militia_service::001",
            "section_heading": "Early vocations and militia service",
            "char_count": 721,
        },
        {
            "chunk_id": "Q91::illinois_state_legislature_1834_1842::000",
            "section_heading": "Illinois state legislature (1834-1842)",
            "char_count": 1607,
        },
        {
            "chunk_id": "Q91::u_s_house_of_representatives_1847_1849::000",
            "section_heading": "U.S. House of Representatives (1847-1849)",
            "char_count": 1653,
        },
        {
            "chunk_id": "Q91::u_s_house_of_representatives_1847_1849::001",
            "section_heading": "U.S. House of Representatives (1847-1849)",
            "char_count": 942,
        },
        {"chunk_id": "Q91::prairie_lawyer::000", "section_heading": "Prairie lawyer", "char_count": 1227},
    ],
}


# ---------------------------------------------------------------------------
# Frontend assets
#
# The operator UI is a React/Vite SPA under wiki_collab/frontend/. Its built
# output (frontend/dist/) is served from this same http.server, so a
# collaborator still only runs `python demo_app.py` with no node/npm at run
# time. Build it once with `npm install && npm run build` inside frontend/.
#
# The previous UI lived here as two ~840-line Python raw strings (a dead copy
# plus the live hand-rolled vanilla-JS page); both have been removed in favor
# of the typed, componentized React cockpit.
# ---------------------------------------------------------------------------
FRONTEND_DIST = Path(__file__).resolve().with_name("frontend") / "dist"

FALLBACK_HTML = (
    "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
    "<title>Persona Curation Cockpit</title>"
    "<style>body{font-family:ui-sans-serif,system-ui,sans-serif;max-width:46rem;"
    "margin:4rem auto;padding:0 1.5rem;color:#1f2933;line-height:1.6}"
    "code,pre{background:#f1f5f9;padding:.15rem .4rem;border-radius:.35rem;"
    "font-family:ui-monospace,monospace}pre{padding:1rem;overflow:auto}"
    "h1{font-size:1.4rem}</style></head><body>"
    "<h1>Persona Curation Cockpit — frontend not built</h1>"
    "<p>The React SPA has not been built yet. From the repository root:</p>"
    "<pre><code>cd personas/existing_data_curation/wiki_collab/frontend\n"
    "npm install\nnpm run build</code></pre>"
    "<p>Then reload. The JSON API is already live at <code>/api/state</code> "
    "and <code>/api/dimensions</code>.</p></body></html>"
)


@dataclass
class DemoWorkspace:
    root: Path
    db_path: Path
    dataset_manifest_path: Path
    assignments_path: Path
    packages_dir: Path
    runs_dir: Path
    inbox_dir: Path
    reports_dir: Path
    protocol_dir: Path
    merged_results_path: Path
    dataset_manifest: dict[str, Any]
    assignments: list[Assignment]


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        drop table if exists profiles;
        create table profiles (
          global_idx integer primary key,
          task_id text not null unique,
          page_id integer not null,
          qid text not null,
          title text not null,
          source_url text not null,
          profile_text text not null,
          input_sha256 text not null,
          source_file text not null,
          source_row integer not null
        );
        create index profiles_qid_idx on profiles(qid);
        create index profiles_title_idx on profiles(title);
        """
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_assignments(path: Path, assignments: list[Assignment]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for assignment in assignments:
            fh.write(json.dumps(assignment.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def _load_assignments(path: Path) -> list[Assignment]:
    if not path.exists():
        return []
    return [Assignment.from_dict(row) for row in load_jsonl(path)]


def _build_demo_db(db_path: Path, manifest_path: Path) -> dict[str, Any]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = _connect(db_path)
    _create_schema(conn)
    for global_idx, row in enumerate(DEMO_PROFILES):
        task_id = f"wiki_profile:{global_idx:010d}"
        payload = profile_input_payload(
            {
                "global_idx": global_idx,
                "task_id": task_id,
                "qid": row["qid"],
                "title": row["title"],
                "source_url": row["source_url"],
                "profile_text": row["profile_text"],
            }
        )
        conn.execute(
            """
            insert into profiles (
              global_idx, task_id, page_id, qid, title, source_url,
              profile_text, input_sha256, source_file, source_row
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                global_idx,
                task_id,
                int(row["page_id"]),
                str(row["qid"]),
                str(row["title"]),
                str(row["source_url"]),
                str(row["profile_text"]),
                compute_input_sha256(payload),
                "embedded_demo_profiles",
                global_idx + 1,
            ),
        )
    conn.commit()
    conn.close()
    manifest = {
        "dataset_id": "wiki-persona-demo-20260601",
        "row_count": len(DEMO_PROFILES),
        "db_file": db_path.name,
        "db_sha256": sha256_file(db_path),
        "source_dir": "embedded demo sample from enwiki-20260601 person_text_derivatives",
        "index_rule": "embedded rows sorted for deterministic live demo",
        "profile_text_max_chars": None,
        "format": "sqlite",
    }
    _write_json(manifest_path, manifest)
    return manifest


def _default_assignment(manifest: dict[str, Any], protocol_dir: Path) -> Assignment:
    protocol = load_protocol_manifest(protocol_dir)
    return Assignment(
        assignment_id="DEMO-0001",
        worker_id="local-claude-demo",
        dataset_id=str(manifest["dataset_id"]),
        dataset_sha256=str(manifest["db_sha256"]),
        protocol_id=protocol.protocol_id,
        protocol_sha256=protocol.protocol_sha256,
        range_start=0,
        range_end=min(int(manifest["row_count"]), 1),
    )


def ensure_demo_workspace(
    root: Path = DEFAULT_DEMO_ROOT,
    protocol_dir: Path = DEFAULT_PROTOCOL_DIR,
) -> DemoWorkspace:
    root = Path(root)
    db_path = root / "profiles.sqlite"
    dataset_manifest_path = root / "dataset_manifest.json"
    assignments_path = root / "assignments.jsonl"
    packages_dir = root / "packages"
    runs_dir = root / "runs"
    inbox_dir = root / "inbox"
    reports_dir = root / "reports"
    merged_results_path = root / "merged" / "accepted_results.jsonl.gz"

    for path in (packages_dir, runs_dir, inbox_dir, reports_dir, merged_results_path.parent):
        path.mkdir(parents=True, exist_ok=True)

    if not db_path.exists() or not dataset_manifest_path.exists():
        manifest = _build_demo_db(db_path, dataset_manifest_path)
    else:
        manifest = json.loads(dataset_manifest_path.read_text(encoding="utf-8"))

    assignments = _load_assignments(assignments_path)
    if not assignments:
        assignments = [_default_assignment(manifest, protocol_dir)]
        _write_assignments(assignments_path, assignments)

    return DemoWorkspace(
        root=root,
        db_path=db_path,
        dataset_manifest_path=dataset_manifest_path,
        assignments_path=assignments_path,
        packages_dir=packages_dir,
        runs_dir=runs_dir,
        inbox_dir=inbox_dir,
        reports_dir=reports_dir,
        protocol_dir=protocol_dir,
        merged_results_path=merged_results_path,
        dataset_manifest=manifest,
        assignments=assignments,
    )


def _runtime_protocol_dir(workspace: DemoWorkspace) -> Path:
    return workspace.root / "runtime_protocol"


def active_protocol_dir(workspace: DemoWorkspace) -> Path:
    runtime = _runtime_protocol_dir(workspace)
    if (runtime / "protocol_manifest.json").exists() and (runtime / "prompt.md").exists():
        return runtime
    return workspace.protocol_dir


def materialize_protocol_for_prompt(
    workspace: DemoWorkspace,
    prompt_text: str | None,
) -> Path:
    if prompt_text is None or not prompt_text.strip():
        return active_protocol_dir(workspace)
    runtime = _runtime_protocol_dir(workspace)
    if runtime.exists():
        shutil.rmtree(runtime)
    runtime.mkdir(parents=True, exist_ok=True)
    for filename in ("protocol_manifest.json", "input.schema.json", "output.schema.json"):
        shutil.copy2(workspace.protocol_dir / filename, runtime / filename)
    (runtime / "prompt.md").write_text(prompt_text.rstrip() + "\n", encoding="utf-8")
    return runtime


def demo_selected_input(workspace: DemoWorkspace, global_idx: int = 0) -> dict[str, Any]:
    conn = _connect(workspace.db_path)
    row = conn.execute(
        """
        select global_idx, task_id, qid, title, source_url, profile_text
        from profiles
        where global_idx = ?
        """,
        (global_idx,),
    ).fetchone()
    conn.close()
    if row is None:
        raise ValueError(f"no demo profile at global_idx {global_idx}")
    return profile_input_payload(dict(row))


def create_assignment(
    workspace: DemoWorkspace,
    *,
    worker_id: str,
    range_start: int,
    range_end: int,
    protocol_dir: Path | None = None,
) -> Assignment:
    row_count = int(workspace.dataset_manifest["row_count"])
    if not worker_id.strip():
        raise ValueError("worker_id is required")
    if range_start < 0 or range_end <= range_start or range_end > row_count:
        raise ValueError(f"range must satisfy 0 <= start < end <= {row_count}")
    protocol = load_protocol_manifest(protocol_dir or active_protocol_dir(workspace))
    assignment = Assignment(
        assignment_id=f"DEMO-{int(time.time())}",
        worker_id=worker_id.strip(),
        dataset_id=str(workspace.dataset_manifest["dataset_id"]),
        dataset_sha256=str(workspace.dataset_manifest["db_sha256"]),
        protocol_id=protocol.protocol_id,
        protocol_sha256=protocol.protocol_sha256,
        range_start=range_start,
        range_end=range_end,
    )
    _write_assignments(workspace.assignments_path, [assignment])
    return assignment


def create_assignment_package(workspace: DemoWorkspace, assignment: Assignment) -> Path:
    package_name = (
        f"assignment_{safe_name(assignment.worker_id)}_{assignment.range_start:04d}_"
        f"{assignment.range_end:04d}.tar.gz"
    )
    package_path = workspace.packages_dir / package_name
    if package_path.exists():
        package_path.unlink()

    assignment_json = json.dumps(assignment.to_dict(), ensure_ascii=False, indent=2).encode("utf-8")
    manifest_json = json.dumps(workspace.dataset_manifest, ensure_ascii=False, indent=2).encode("utf-8")

    with tarfile.open(package_path, "w:gz") as tar:
        for name, data in (
            ("assignment.json", assignment_json),
            ("dataset_manifest.json", manifest_json),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = int(time.time())
            tar.addfile(info, fileobj=_BytesReader(data))
        tar.add(workspace.db_path, arcname="profiles.sqlite")
        protocol_dir = active_protocol_dir(workspace)
        for protocol_file in (
            "protocol_manifest.json",
            "prompt.md",
            "input.schema.json",
            "output.schema.json",
        ):
            source = protocol_dir / protocol_file
            if source.exists():
                tar.add(source, arcname=f"protocol/{protocol_file}")
    return package_path


class _BytesReader:
    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            size = len(self._data) - self._pos
        start = self._pos
        end = min(len(self._data), self._pos + size)
        self._pos = end
        return self._data[start:end]


def _ensure_backend_command(backend_name: str) -> None:
    if backend_name == "claude-code-acp":
        command = f"{shlex.quote(sys.executable)} {shlex.quote(str(CLAUDE_WRAPPER))}"
        os.environ.setdefault("WIKI_COLLAB_CLAUDE_CMD", command)
        os.environ.setdefault("WIKI_COLLAB_COMMAND_TIMEOUT", "900")


def run_demo_assignment(
    workspace: DemoWorkspace,
    assignment: Assignment,
    *,
    backend_name: str,
    model: str | None,
    effort: str,
    concurrency: int,
    prompt_text: str | None = None,
) -> Path:
    _ensure_backend_command(backend_name)
    protocol_dir = materialize_protocol_for_prompt(workspace, prompt_text)
    protocol = load_protocol_manifest(protocol_dir)
    if assignment.protocol_sha256 != protocol.protocol_sha256:
        assignment = Assignment(
            assignment_id=assignment.assignment_id,
            worker_id=assignment.worker_id,
            dataset_id=assignment.dataset_id,
            dataset_sha256=assignment.dataset_sha256,
            protocol_id=protocol.protocol_id,
            protocol_sha256=protocol.protocol_sha256,
            range_start=assignment.range_start,
            range_end=assignment.range_end,
            status=assignment.status,
        )
        _write_assignments(workspace.assignments_path, [assignment])
    return run_range(
        db_path=workspace.db_path,
        protocol_dir=protocol_dir,
        range_start=assignment.range_start,
        range_end=assignment.range_end,
        backend_name=backend_name,
        model=model,
        concurrency=concurrency,
        effort=effort,
        worker_id=assignment.worker_id,
        out_dir=workspace.runs_dir,
        dataset_id=assignment.dataset_id,
        dataset_sha256=assignment.dataset_sha256,
        max_attempts=1,
    )


def return_archive(workspace: DemoWorkspace, archive_path: Path) -> Path:
    archive_path = Path(archive_path)
    if not archive_path.exists():
        raise FileNotFoundError(f"archive not found: {archive_path}")
    returned = workspace.inbox_dir / archive_path.name
    if returned.exists():
        returned.unlink()
    shutil.copy2(archive_path, returned)
    return returned


def _returned_archives(workspace: DemoWorkspace) -> list[Path]:
    return sorted(workspace.inbox_dir.glob("*.tar.gz"))


def audit_returned_archives(workspace: DemoWorkspace) -> dict[str, Any]:
    protocol = load_protocol_manifest(active_protocol_dir(workspace))
    report = audit_archives(
        archives=_returned_archives(workspace),
        db_path=workspace.db_path,
        assignments=_load_assignments(workspace.assignments_path),
        expected_prompt_sha256=protocol.prompt_sha256,
    )
    _write_json(workspace.reports_dir / "audit_report.json", report)
    return report


def merge_returned_archives(workspace: DemoWorkspace) -> dict[str, int]:
    report = audit_returned_archives(workspace)
    accepted = [
        Path(item["archive_path"])
        for item in report["archives"]
        if item.get("accepted") and Path(item["archive_path"]).exists()
    ]
    if workspace.merged_results_path.exists():
        workspace.merged_results_path.unlink()
    if not accepted:
        workspace.merged_results_path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(workspace.merged_results_path, "wt", encoding="utf-8"):
            pass
        return {
            "input_rows": 0,
            "written_rows": 0,
            "duplicate_rows": 0,
            "total_rows_after_merge": 0,
        }
    return merge_archives(accepted, workspace.merged_results_path)


def reset_outputs(workspace: DemoWorkspace) -> None:
    for directory in (workspace.packages_dir, workspace.runs_dir, workspace.inbox_dir, workspace.reports_dir):
        for item in directory.glob("*"):
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    if workspace.merged_results_path.exists():
        workspace.merged_results_path.unlink()


def _normalize_lookup(value: Any) -> str:
    return str(value or "").strip().casefold()


def _match_page_row(row: dict[str, Any], query: str) -> bool:
    normalized = _normalize_lookup(query)
    return normalized in {
        _normalize_lookup(row.get("title")),
        _normalize_lookup(row.get("qid")),
        _normalize_lookup(row.get("page_id")),
    }


def _iter_gzip_jsonl(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def _rows_for_page(path: Path, clean_row: dict[str, Any]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    page_id = clean_row.get("page_id")
    qid = clean_row.get("qid")
    title = clean_row.get("title")
    rows = [
        row
        for row in _iter_gzip_jsonl(path)
        if row.get("page_id") == page_id or row.get("qid") == qid or row.get("title") == title
    ]
    return rows


def load_full_clean_page(derivatives_dir: Path, query: str) -> dict[str, Any]:
    start = time.time()
    root = Path(derivatives_dir)
    clean_dir = root / "person_pages_clean"
    sections_dir = root / "person_page_sections"
    chunks_dir = root / "person_page_chunks"
    if not clean_dir.exists():
        return {
            "found": False,
            "query": query,
            "error": f"clean page directory not found: {clean_dir}",
            "elapsed_seconds": round(time.time() - start, 3),
        }

    clean_row = None
    clean_file = None
    scanned_files = 0
    scanned_rows = 0
    for path in sorted(clean_dir.glob("part-*.jsonl.gz")):
        scanned_files += 1
        for row in _iter_gzip_jsonl(path):
            scanned_rows += 1
            if _match_page_row(row, query):
                clean_row = row
                clean_file = path
                break
        if clean_row is not None:
            break

    if clean_row is None or clean_file is None:
        return {
            "found": False,
            "query": query,
            "error": "page not found in clean derivative shards",
            "scanned_files": scanned_files,
            "scanned_rows": scanned_rows,
            "elapsed_seconds": round(time.time() - start, 3),
        }

    shard_name = clean_file.name
    sections = _rows_for_page(sections_dir / shard_name, clean_row)
    chunks = _rows_for_page(chunks_dir / shard_name, clean_row)
    sections.sort(key=lambda row: (int(row.get("section_index", 0)), str(row.get("section_id", ""))))
    chunks.sort(key=lambda row: (int(row.get("section_index", 0)), int(row.get("chunk_index", 0)), str(row.get("chunk_id", ""))))
    return {
        "found": True,
        "query": query,
        "clean": clean_row,
        "sections": sections,
        "chunks": chunks,
        "source": {
            "derivatives_dir": str(root),
            "clean_file": str(clean_file.relative_to(root)),
            "sections_file": str((sections_dir / shard_name).relative_to(root)),
            "chunks_file": str((chunks_dir / shard_name).relative_to(root)),
        },
        "scanned_files": scanned_files,
        "scanned_rows": scanned_rows,
        "elapsed_seconds": round(time.time() - start, 3),
    }


def _db_profiles(workspace: DemoWorkspace) -> list[dict[str, Any]]:
    conn = _connect(workspace.db_path)
    rows = [
        dict(row)
        for row in conn.execute(
            """
            select global_idx, task_id, page_id, qid, title, source_url, profile_text, input_sha256
            from profiles
            order by global_idx
            """
        )
    ]
    conn.close()
    details = {row["qid"]: row for row in DEMO_PROFILES}
    out = []
    for row in rows:
        detail = details.get(row["qid"], {})
        out.append(
            {
                **row,
                "entity_type": detail.get("entity_type", "real_person"),
                "tags": detail.get("tags", []),
                "revision_id": detail.get("revision_id"),
                "revision_timestamp": detail.get("revision_timestamp"),
                "sections": detail.get("sections", []),
                "chunks": detail.get("chunks", []),
            }
        )
    return out


def _file_link(workspace: DemoWorkspace, path: Path | None) -> dict[str, str] | None:
    if path is None or not path.exists():
        return None
    path = path.resolve()
    try:
        rel = path.relative_to(workspace.root.resolve())
    except ValueError:
        return {"path": str(path), "href": "#"}
    return {"path": str(path), "href": f"/files/{rel.as_posix()}"}


def _latest(path: Path, pattern: str) -> Path | None:
    items = sorted(path.glob(pattern), key=lambda item: item.stat().st_mtime)
    return items[-1] if items else None


def _read_gzip_jsonl_from_archive(archive_path: Path, member_name: str) -> list[dict[str, Any]]:
    with tarfile.open(archive_path, "r:gz") as tar:
        try:
            member = tar.getmember(member_name)
        except KeyError:
            return []
        fh = tar.extractfile(member)
        if fh is None:
            return []
        data = gzip.decompress(fh.read()).decode("utf-8")
    return [json.loads(line) for line in data.splitlines() if line.strip()]


def _demo_title_for_qid(qid: str | None) -> str | None:
    if not qid:
        return None
    for profile in DEMO_PROFILES:
        if profile.get("qid") == qid:
            return str(profile.get("title"))
    return None


def _plain_field_meaning(field: dict[str, Any]) -> str:
    field_id = str(field.get("field_id") or "unknown_field")
    value = field.get("value")
    if value is None:
        value_text = "unsupported / null"
    elif isinstance(value, (dict, list)):
        value_text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        value_text = str(value)
    return f"{field_id} = {value_text}"


def preview_result_archive(archive_path: Path, limit: int = 5) -> dict[str, Any]:
    archive_path = Path(archive_path)
    rows = _read_gzip_jsonl_from_archive(archive_path, "results.jsonl.gz")
    failures = _read_gzip_jsonl_from_archive(archive_path, "failures.jsonl.gz")
    preview_rows: list[dict[str, Any]] = []
    for row in rows[: max(0, limit)]:
        fields = []
        for field in row.get("fields", []):
            if not isinstance(field, dict):
                continue
            fields.append(
                {
                    "field_id": field.get("field_id"),
                    "value": field.get("value"),
                    "confidence": field.get("confidence"),
                    "assignment_type": field.get("assignment_type"),
                    "evidence": field.get("evidence"),
                    "plain_meaning": _plain_field_meaning(field),
                }
            )
        preview_rows.append(
            {
                "global_idx": row.get("global_idx"),
                "task_id": row.get("task_id"),
                "qid": row.get("qid"),
                "title": _demo_title_for_qid(row.get("qid")) or row.get("qid") or "unknown",
                "status": row.get("status"),
                "input_sha256": row.get("input_sha256"),
                "fields": fields,
                "provenance": row.get("provenance", {}),
            }
        )
    return {
        "archive_path": str(archive_path),
        "row_count": len(rows),
        "failure_count": len(failures),
        "preview_limit": limit,
        "rows": preview_rows,
    }


_DIMENSIONS_PATH = REPO_ROOT / "personas" / "dimensions+new.json"
_DIMENSION_CATALOG_CACHE: dict[str, Any] | None = None


def _dim_slug(category: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", category.strip().lower()).strip("_")
    return cleaned or "uncategorized"


def dimension_catalog() -> dict[str, Any]:
    """The 1339-dimension catalog grouped by category (GET /api/dimensions).

    Each category carries its dimensions ({id,label,description,values}) plus the
    per-category protocol_id, so the frontend can join model output (field_id ==
    dimension id) onto the taxonomy and link a category to its dispatch protocol.
    Cached: the catalog is static for the process lifetime.
    """
    global _DIMENSION_CATALOG_CACHE
    if _DIMENSION_CATALOG_CACHE is not None:
        return _DIMENSION_CATALOG_CACHE
    if not _DIMENSIONS_PATH.exists():
        payload = {"total_dimensions": 0, "category_count": 0, "categories": []}
        _DIMENSION_CATALOG_CACHE = payload
        return payload
    data = json.loads(_DIMENSIONS_PATH.read_text(encoding="utf-8"))
    dims = data.get("dimensions", [])
    groups: dict[str, list[dict[str, Any]]] = {}
    for dim in dims:
        groups.setdefault(str(dim.get("category", "Uncategorized")), []).append(dim)
    categories = []
    for category, cat_dims in groups.items():
        slug = _dim_slug(category)
        categories.append(
            {
                "category": category,
                "slug": slug,
                "protocol_id": f"persona_attribution_{slug}",
                "count": len(cat_dims),
                "dimensions": [
                    {
                        "id": str(d["id"]),
                        "label": str(d.get("label", d["id"])),
                        "description": str(d.get("description", "")),
                        "values": list(d.get("values", [])),
                    }
                    for d in cat_dims
                ],
            }
        )
    payload = {
        "total_dimensions": len(dims),
        "category_count": len(groups),
        "categories": categories,
    }
    _DIMENSION_CATALOG_CACHE = payload
    return payload


def state_payload(workspace: DemoWorkspace) -> dict[str, Any]:
    audit_path = workspace.reports_dir / "audit_report.json"
    audit_report = None
    if audit_path.exists():
        audit_report = json.loads(audit_path.read_text(encoding="utf-8"))
    latest_result_archive = _latest(workspace.inbox_dir, "*.tar.gz") or _latest(workspace.runs_dir, "*.tar.gz")
    result_preview = preview_result_archive(latest_result_archive) if latest_result_archive else None
    protocol_dir = active_protocol_dir(workspace)
    protocol = load_protocol_manifest(protocol_dir)
    prompt_template = (protocol_dir / protocol.prompt_file).read_text(encoding="utf-8")
    selected_input = demo_selected_input(workspace, 0)
    rendered_prompt = render_prompt(prompt_template, selected_input)
    return {
        "root": str(workspace.root),
        "metrics": {
            "clean_pages": 2_125_897,
            "sections": 7_406_458,
            "chunks": 7_852_032,
            "plain_text_chars": 6_102_567_572,
            "markup_residue_rows": 0,
            "demo_rows": int(workspace.dataset_manifest["row_count"]),
        },
        "dataset_manifest": workspace.dataset_manifest,
        "full_page_derivatives": {
            "path": str(DEFAULT_DERIVATIVES_DIR),
            "available": (DEFAULT_DERIVATIVES_DIR / "person_pages_clean").exists(),
        },
        "lincoln_full_article": LINCOLN_FULL_ARTICLE_FOOTPRINT,
        "protocol_manifest": protocol.to_dict(),
        "prompt_template": prompt_template,
        "selected_input": selected_input,
        "rendered_prompt": rendered_prompt,
        "profiles": _db_profiles(workspace),
        "assignment": workspace.assignments[0].to_dict() if workspace.assignments else None,
        "backend_status": {
            "claude_bin": shutil.which("claude"),
            "codex_bin": shutil.which("codex"),
            "claude_command": os.environ.get(
                "WIKI_COLLAB_CLAUDE_CMD",
                f"{sys.executable} {CLAUDE_WRAPPER}",
            ),
            "claude_cli_model_env": os.environ.get("WIKI_COLLAB_CLAUDE_CLI_MODEL", "opus"),
        },
        "files": {
            "assignment_package": _file_link(workspace, _latest(workspace.packages_dir, "*.tar.gz")),
            "last_run_archive": _file_link(workspace, _latest(workspace.runs_dir, "*.tar.gz")),
            "last_returned_archive": _file_link(workspace, _latest(workspace.inbox_dir, "*.tar.gz")),
            "audit_report": _file_link(workspace, audit_path if audit_path.exists() else None),
            "merged_results": _file_link(
                workspace,
                workspace.merged_results_path if workspace.merged_results_path.exists() else None,
            ),
        },
        "audit_report": audit_report,
        "result_preview": result_preview,
    }


class DemoHandler(BaseHTTPRequestHandler):
    server: "DemoServer"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[demo] " + fmt % args + "\n")

    def _workspace(self) -> DemoWorkspace:
        self.server.workspace = ensure_demo_workspace(self.server.workspace.root)
        return self.server.workspace

    def _json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _html(self) -> None:
        index_html = FRONTEND_DIST / "index.html"
        if index_html.is_file():
            data = index_html.read_bytes()
        else:
            data = FALLBACK_HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_dist(self, rel: str) -> bool:
        """Serve a built SPA asset from FRONTEND_DIST (inline, traversal-guarded).

        Returns True if the request was handled (served or 404'd as a known
        asset path), False if the caller should fall through to other routes.
        """
        root = FRONTEND_DIST.resolve()
        if not root.exists():
            return False
        path = (root / Path(unquote(rel.lstrip("/")))).resolve()
        if root != path and root not in path.parents:
            self.send_error(HTTPStatus.FORBIDDEN.value)
            return True
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND.value)
            return True
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        return True

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._html()
            return
        if parsed.path == "/api/state":
            self._json(state_payload(self._workspace()))
            return
        if parsed.path == "/api/dimensions":
            self._json(dimension_catalog())
            return
        if parsed.path.startswith("/files/"):
            self._send_file(parsed.path.removeprefix("/files/"))
            return
        # Built SPA assets (e.g. /assets/index-*.js, /favicon.svg).
        if self._serve_dist(parsed.path):
            return
        self.send_error(HTTPStatus.NOT_FOUND.value)

    def do_POST(self) -> None:
        try:
            body = self._body()
            workspace = self._workspace()
            if self.path == "/api/assignment":
                protocol_dir = materialize_protocol_for_prompt(
                    workspace,
                    body.get("prompt_text") if isinstance(body.get("prompt_text"), str) else None,
                )
                assignment = create_assignment(
                    workspace,
                    worker_id=str(body.get("worker_id") or "local-claude-demo"),
                    range_start=int(body.get("range_start", 0)),
                    range_end=int(body.get("range_end", 1)),
                    protocol_dir=protocol_dir,
                )
                workspace = ensure_demo_workspace(workspace.root)
                package = create_assignment_package(workspace, assignment)
                self.server.workspace = workspace
                self._json(
                    {
                        "assignment": assignment.to_dict(),
                        "package": _file_link(workspace, package),
                    }
                )
                return
            if self.path == "/api/run":
                assignment = workspace.assignments[0]
                archive = run_demo_assignment(
                    workspace,
                    assignment,
                    backend_name=str(body.get("backend_name") or "mock"),
                    model=body.get("model") or None,
                    effort=str(body.get("effort") or "high"),
                    concurrency=max(1, int(body.get("concurrency", 1))),
                    prompt_text=body.get("prompt_text") if isinstance(body.get("prompt_text"), str) else None,
                )
                self._json({"archive": _file_link(workspace, archive), "assignment": assignment.to_dict()})
                return
            if self.path == "/api/full-page":
                query = str(body.get("query") or "").strip()
                if not query:
                    raise ValueError("query is required")
                self._json(load_full_clean_page(DEFAULT_DERIVATIVES_DIR, query))
                return
            if self.path == "/api/return":
                archive_raw = body.get("archive")
                archive = Path(archive_raw) if archive_raw else _latest(workspace.runs_dir, "*.tar.gz")
                if archive is None:
                    raise FileNotFoundError("no run archive available")
                returned = return_archive(workspace, archive)
                self._json({"returned": _file_link(workspace, returned)})
                return
            if self.path == "/api/audit":
                report = audit_returned_archives(workspace)
                self._json({"report": report})
                return
            if self.path == "/api/merge":
                summary = merge_returned_archives(workspace)
                self._json({"summary": summary, "merged": _file_link(workspace, workspace.merged_results_path)})
                return
            if self.path == "/api/reset":
                reset_outputs(workspace)
                self._json({"ok": True})
                return
            self.send_error(HTTPStatus.NOT_FOUND.value)
        except Exception as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _send_file(self, raw_rel: str) -> None:
        workspace = self._workspace()
        rel = Path(unquote(raw_rel))
        root = workspace.root.resolve()
        path = (root / rel).resolve()
        if root not in path.parents and path != root:
            self.send_error(HTTPStatus.FORBIDDEN.value)
            return
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND.value)
            return
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.end_headers()
        self.wfile.write(data)


class DemoServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], workspace: DemoWorkspace):
        super().__init__(server_address, DemoHandler)
        self.workspace = workspace


def serve(host: str, port: int, root: Path) -> DemoServer:
    workspace = ensure_demo_workspace(root)
    server = DemoServer((host, port), workspace)
    print(f"Wiki collaboration demo: http://{host}:{server.server_port}")
    print(f"Workspace: {workspace.root}")
    return server


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--root", type=Path, default=DEFAULT_DEMO_ROOT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    server = serve(args.host, args.port, args.root)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping demo server")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
