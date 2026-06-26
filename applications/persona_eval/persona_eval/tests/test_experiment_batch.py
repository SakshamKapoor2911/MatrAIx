from __future__ import annotations

import json
import threading
import time

from persona_eval.experiments.applications import ApplicationSpec
from persona_eval.experiments.batch import ExperimentBatchRunner, build_run_specs
from persona_eval.experiments.models import ExperimentRunResult
from persona_eval.types import Persona


def test_batch_runner_writes_manifest_results_and_summary(tmp_path):
    personas = [
        Persona(id="p1", name="Persona 1"),
        Persona(id="p2", name="Persona 2"),
    ]
    application = ApplicationSpec(
        key="fake:chatbot",
        application_type="chatbot",
        application_id="fake",
        application_context="context",
        domain="context",
        label="Fake chatbot",
        system_label="fake system",
        description_key="movie",
        concurrency_limit=2,
    )
    specs = build_run_specs(
        personas=personas,
        applications=[application],
        api_url="http://fake.local",
        persona_model="fake-persona",
        max_turns=1,
        min_turns=1,
        goal_context_id="scenario_default",
    )

    def run_one(spec, _persona, output_dir, _application):
        output_dir.mkdir(parents=True)
        (output_dir / "events.ndjson").write_text("{}\n", encoding="utf-8")
        return ExperimentRunResult(
            run_id=spec.run_id,
            status="done",
            output_dir=output_dir,
            started_at="start",
            finished_at="finish",
            artifacts=["events.ndjson"],
        )

    summary = ExperimentBatchRunner(
        applications=[application],
        personas=personas,
        run_one=run_one,
        now=lambda: "now",
    ).run_batch(specs, output_dir=tmp_path, max_workers=4)

    assert summary["total"] == 2
    assert summary["statusCounts"] == {"done": 2}
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert len(manifest["runs"]) == 2
    result_lines = (tmp_path / "results.ndjson").read_text().splitlines()
    assert len(result_lines) == 2
    persisted_summary = json.loads((tmp_path / "summary.json").read_text())
    assert persisted_summary["completed"] == 2


def test_batch_runner_respects_application_concurrency_limit(tmp_path):
    personas = [Persona(id="p{}".format(index), name="Persona {}".format(index)) for index in range(4)]
    application = ApplicationSpec(
        key="limited:chatbot",
        application_type="chatbot",
        application_id="limited",
        application_context="context",
        domain="context",
        label="Limited chatbot",
        system_label="limited system",
        description_key="movie",
        concurrency_limit=1,
    )
    specs = build_run_specs(
        personas=personas,
        applications=[application],
        api_url="http://fake.local",
        persona_model="fake-persona",
        max_turns=1,
        min_turns=1,
        goal_context_id="scenario_default",
    )
    active = 0
    max_active = 0
    lock = threading.Lock()

    def run_one(spec, _persona, output_dir, _application):
        nonlocal active, max_active
        output_dir.mkdir(parents=True)
        with lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.02)
        with lock:
            active -= 1
        return ExperimentRunResult(
            run_id=spec.run_id,
            status="done",
            output_dir=output_dir,
            started_at="start",
            finished_at="finish",
        )

    ExperimentBatchRunner(
        applications=[application],
        personas=personas,
        run_one=run_one,
        now=lambda: "now",
    ).run_batch(specs, output_dir=tmp_path, max_workers=4)

    assert max_active == 1
