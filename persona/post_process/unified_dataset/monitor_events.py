#!/usr/bin/env python3
"""Event-driven monitor for the active Persona8B materialization and upload."""

from __future__ import annotations

from collections import Counter
import ctypes
from datetime import datetime
import json
import os
from pathlib import Path
import select
import struct
import subprocess
import sys


ROOT = Path(__file__).parent / "results/persona8b_8_4b_20260720"
REPORTS = ROOT / "reports"
CURRENT_LOGS = Path("/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/sbatch_logs")
JOB_IDS = ("33386504", "33386505", "33386507", "33386509", "33386510")
UPLOAD_JOB = "33386510"

IN_CREATE = 0x00000100
IN_MODIFY = 0x00000002
IN_CLOSE_WRITE = 0x00000008
IN_MOVED_TO = 0x00000080
WATCH_MASK = IN_CREATE | IN_MODIFY | IN_CLOSE_WRITE | IN_MOVED_TO
EVENT_HEADER = struct.Struct("iIII")


def _job_states() -> dict[str, Counter[str]]:
    result = subprocess.run(
        [
            "sacct",
            "-X",
            "-n",
            "-j",
            ",".join(JOB_IDS),
            "--format=JobIDRaw,State",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    states: dict[str, Counter[str]] = {job_id: Counter() for job_id in JOB_IDS}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        job_id, state = parts[0], parts[1].split("+")[0]
        root_id = job_id.split("_")[0]
        if root_id in states:
            states[root_id][state] += 1
    return states


def _progress() -> dict[str, object]:
    rows = Counter()
    bytes_by_source = Counter()
    descriptions = Counter()
    reports = sorted(REPORTS.glob("*.json"))
    for path in reports:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        source = report["source"]
        rows[source] += int(report["rows"])
        bytes_by_source[source] += int(report["bytes"])
        descriptions[source] += int(report.get("description_rows", 0))
    return {
        "time": datetime.now().isoformat(timespec="seconds"),
        "reports": len(reports),
        "rows": dict(sorted(rows.items())),
        "bytes": dict(sorted(bytes_by_source.items())),
        "description_rows": dict(sorted(descriptions.items())),
        "manifest_ready": (ROOT / "manifest.json").is_file(),
        "jobs": {job_id: dict(counter) for job_id, counter in _job_states().items()},
    }


def _upload_state(progress: dict[str, object]) -> str | None:
    jobs = progress["jobs"]
    assert isinstance(jobs, dict)
    upload = jobs.get(UPLOAD_JOB, {})
    assert isinstance(upload, dict)
    for state in ("COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY"):
        if upload.get(state):
            return state
    return None


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    CURRENT_LOGS.mkdir(parents=True, exist_ok=True)
    libc = ctypes.CDLL("libc.so.6", use_errno=True)
    inotify_init1 = libc.inotify_init1
    inotify_init1.argtypes = [ctypes.c_int]
    inotify_init1.restype = ctypes.c_int
    inotify_add_watch = libc.inotify_add_watch
    inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
    inotify_add_watch.restype = ctypes.c_int
    descriptor = inotify_init1(os.O_NONBLOCK)
    if descriptor < 0:
        raise OSError(ctypes.get_errno(), "inotify_init1 failed")
    watches = {}
    for path in (REPORTS, ROOT, CURRENT_LOGS):
        watch = inotify_add_watch(descriptor, os.fsencode(path), WATCH_MASK)
        if watch < 0:
            raise OSError(ctypes.get_errno(), f"inotify_add_watch failed: {path}")
        watches[watch] = path

    progress = _progress()
    print(json.dumps(progress, sort_keys=True), flush=True)
    while True:
        state = _upload_state(progress)
        if state == "COMPLETED":
            return
        if state in {"FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY"}:
            raise RuntimeError(f"Upload job ended in {state}")
        readable, _, _ = select.select([descriptor], [], [])
        if not readable:
            continue
        payload = os.read(descriptor, 1024 * 1024)
        offset = 0
        interesting = False
        while offset + EVENT_HEADER.size <= len(payload):
            watch, mask, _, name_length = EVENT_HEADER.unpack_from(payload, offset)
            offset += EVENT_HEADER.size
            name = payload[offset : offset + name_length].rstrip(b"\0").decode(errors="replace")
            offset += name_length
            if mask & (IN_CLOSE_WRITE | IN_MOVED_TO | IN_CREATE):
                path = watches.get(watch)
                if path == REPORTS and name.endswith(".json"):
                    interesting = True
                elif path == ROOT and name in {"manifest.json", "README.md"}:
                    interesting = True
                elif path == CURRENT_LOGS and "persona8b_" in name:
                    interesting = True
        if interesting:
            progress = _progress()
            print(json.dumps(progress, sort_keys=True), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"monitor failed: {error}", file=sys.stderr, flush=True)
        raise