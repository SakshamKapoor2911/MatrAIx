from __future__ import annotations

import json
from pathlib import Path

from persona.curation.existing_data.scripts import (
    render_nemotron_domain_selection_plots as renderer,
)
from persona.curation.existing_data.scripts import select_nemotron_survey_users as selector


def write_persona(
    path: Path,
    *,
    age: int,
    gender: str,
    occupation: str,
    state: str,
) -> None:
    path.write_text(
        f"""source: Nemotron
id: {path.stem.removeprefix("Nemotron_")}
record_index: {age}
demographics:
  age: {age}
  gender: {gender}
  marital_status: never_married
  education_level: bachelors
  occupation: {occupation}
  location:
    city: Test City
    state: {state}
    country: USA
    zipcode: "00000"
personas:
  core: Test core persona.
  professional: Test professional persona.
attributes:
  hobbies:
    - Reading
  skills:
    - Writing
""",
        encoding="utf-8",
    )


def test_select_nemotron_survey_users_writes_outputs(tmp_path: Path) -> None:
    curated_dir = tmp_path / "curated"
    output_dir = tmp_path / "out"
    curated_dir.mkdir()
    write_persona(
        curated_dir / "Nemotron_AAAA1111.yaml",
        age=22,
        gender="Female",
        occupation="teacher",
        state="CA",
    )
    write_persona(
        curated_dir / "Nemotron_BBBB2222.yaml",
        age=45,
        gender="Male",
        occupation="software_developer",
        state="TX",
    )
    write_persona(
        curated_dir / "Nemotron_CCCC3333.yaml",
        age=71,
        gender="Female",
        occupation="physician",
        state="NY",
    )

    assert (
        selector.main(
            [
                "--curated-dir",
                str(curated_dir),
                "--output-dir",
                str(output_dir),
                "--sample-size",
                "2",
            ]
        )
        == 0
    )

    payload = json.loads(
        (output_dir / "nemotron_survey_users_50.json").read_text(encoding="utf-8")
    )
    assert payload["candidate_count"] == 3
    assert payload["selected_count"] == 2
    assert (
        (output_dir / "nemotron_survey_user_ids_50.txt")
        .read_text(encoding="utf-8")
        .count("\n")
        == 2
    )
    summary = (output_dir / "nemotron_survey_users_50.md").read_text(encoding="utf-8")
    assert "Selected personas: `2`" in summary


def test_render_nemotron_domain_selection_plots_from_committed_fixtures(
    tmp_path: Path,
) -> None:
    input_dir = Path("persona/curation/existing_data/samples/nemotron_domain_selection")
    assert (
        renderer.main(
            [
                "--input-dir",
                str(input_dir),
                "--output-dir",
                str(tmp_path),
            ]
        )
        == 0
    )

    overall_svg = tmp_path / "nemotron_overall_diversity_projection.svg"
    cluster_svg = tmp_path / "nemotron_within_domain_cluster_projection.svg"
    assert overall_svg.exists()
    assert cluster_svg.exists()
    assert "<svg" in overall_svg.read_text(encoding="utf-8")
