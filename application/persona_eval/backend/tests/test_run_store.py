from backend.service import run_store


def test_persist_and_load_round_trip(tmp_path):
    run_store.persist_run(tmp_path, {"id": "survey_1", "applicationType": "survey"})
    run_store.persist_run(tmp_path, {"id": "web_1", "applicationType": "web"})
    assert run_store.load_run(tmp_path, "survey_1") == {
        "id": "survey_1",
        "applicationType": "survey",
    }
    ids = {r["id"] for r in run_store.iter_run_records(tmp_path)}
    assert ids == {"survey_1", "web_1"}


def test_persist_run_without_id_is_noop(tmp_path):
    run_store.persist_run(tmp_path, {"applicationType": "survey"})
    assert run_store.iter_run_records(tmp_path) == []


def test_summarize_survey_record():
    record = {
        "id": "survey_1",
        "createdAt": "2026-06-27T00:00:00Z",
        "applicationType": "survey",
        "persona": {"name": "Marco", "source": "Nemotron"},
        "surveyResult": {"completion": {"meanLikert": 4.0}},
    }
    s = run_store.summarize_record(record)
    assert s["applicationType"] == "survey"
    assert s["personaName"] == "Marco"
    assert s["source"] == "Nemotron"
    assert s["overallRating"] == 8  # 1-5 Likert mapped to 1-10
    assert s["numTurns"] is None


def test_summarize_web_record():
    record = {
        "id": "web_1",
        "applicationType": "web",
        "persona": {"name": "Ada", "source": "PersonaHub"},
        "webResult": {"overallExperienceRating": 8},
    }
    s = run_store.summarize_record(record)
    assert s["applicationType"] == "web"
    assert s["overallRating"] == 8
    assert s["personaName"] == "Ada"


def test_summarize_chatbot_record():
    record = {
        "id": "job_1",
        "applicationType": "chatbot",
        "persona": {"name": "Marco", "source": "Nemotron"},
        "config": {"domain": "movie", "goalContextId": "scenario_default"},
        "questionnaire": {"overallRating": 7},
        "metricScores": {"numTurns": 5},
    }
    s = run_store.summarize_record(record)
    assert s["applicationType"] == "chatbot"
    assert s["domain"] == "movie"
    assert s["overallRating"] == 7
    assert s["numTurns"] == 5


def test_summarize_sniffs_type_without_explicit_field():
    assert run_store.summarize_record({"id": "a", "surveyResult": {}})["applicationType"] == "survey"
    assert run_store.summarize_record({"id": "b", "webResult": {}})["applicationType"] == "web"
    assert run_store.summarize_record({"id": "c"})["applicationType"] == "chatbot"


def test_friendly_persona_name_prefers_occupation_from_context():
    name = run_store.friendly_persona_name(
        {
            "name": "Nemotron · 01B0D4D4",
            "source": "Nemotron",
            "context": "Demographics:\n  Age: 51\n  Occupation: Financial Manager\n  Location:\n",
        }
    )
    assert name == "Financial Manager"


def test_friendly_persona_name_falls_back_to_name_then_source():
    assert run_store.friendly_persona_name({"name": "Ada Lovelace", "context": "no role here"}) == "Ada Lovelace"
    assert run_store.friendly_persona_name({"name": "", "source": "PersonaHub", "context": ""}) == "PersonaHub"


def test_summarize_survey_record_uses_friendly_name():
    record = {
        "id": "survey_x",
        "applicationType": "survey",
        "persona": {"name": "Nemotron · 01B0D4D4", "source": "Nemotron", "context": "Occupation: Nurse"},
        "surveyResult": {"completion": {"meanLikert": 5.0}},
    }
    assert run_store.summarize_record(record)["personaName"] == "Nurse"
