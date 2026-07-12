"""API contract tests for the /api/synthesis endpoints.

The endpoints are exercised against a small synthetic graph: the test swaps
the app's PersonaSynthesisService for one pointed at a tmp file, so the
23 MB committed graph is never loaded in the test suite.
"""

from __future__ import annotations

import json

import pytest

from backend.service.persona_synthesis_service import PersonaSynthesisService
from backend.tests.test_persona_synthesis_service import SYNTH_GRAPH


@pytest.fixture()
def synthesis_client(client, app, tmp_path):
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(SYNTH_GRAPH), encoding="utf-8")
    app.state.services.persona_synthesis = PersonaSynthesisService(graph_path)
    return client


def test_overview_endpoint(synthesis_client):
    response = synthesis_client.get("/api/synthesis/graph/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["graphNodes"] == 5
    assert [cat["name"] for cat in body["categories"]] == [
        "Demographics", "Latent", "Health",
    ]
    assert body["categories"][0]["attributes"][0]["id"] == "a"


def test_subgraph_endpoint(synthesis_client):
    response = synthesis_client.get(
        "/api/synthesis/graph/subgraph", params={"node": "c", "up": 1, "down": 1}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["center"] == "c"
    assert {n["id"]: n["layer"] for n in body["nodes"]} == {
        "b": -1, "h": -1, "c": 0, "d": 1,
    }


def test_subgraph_unknown_node_is_404(synthesis_client):
    response = synthesis_client.get(
        "/api/synthesis/graph/subgraph", params={"node": "nope"}
    )
    assert response.status_code == 404


def test_subgraph_out_of_range_hops_is_422(synthesis_client):
    response = synthesis_client.get(
        "/api/synthesis/graph/subgraph", params={"node": "c", "up": 9}
    )
    assert response.status_code == 422


def test_node_detail_endpoint(synthesis_client):
    response = synthesis_client.get("/api/synthesis/nodes/c")
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "Condition"
    assert body["values"] == ["p", "q"]
    assert body["type"] == "attribute"


def test_node_detail_unknown_is_404(synthesis_client):
    response = synthesis_client.get("/api/synthesis/nodes/nope")
    assert response.status_code == 404


def test_node_detail_internal_key_error_is_not_mislabeled_404(
    client, app, tmp_path
):
    graph = json.loads(json.dumps(SYNTH_GRAPH))
    condition = next(node for node in graph["nodes"] if node["id"] == "c")
    condition["prior"] = {"q": 0.7}  # Existing node, corrupt mapping misses "p".
    graph_path = tmp_path / "corrupt-prior-graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    app.state.services.persona_synthesis = PersonaSynthesisService(graph_path)

    with pytest.raises(KeyError, match="p"):
        client.get("/api/synthesis/nodes/c")
