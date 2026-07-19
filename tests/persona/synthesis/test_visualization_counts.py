from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
GRAPH_PATH = ROOT / "persona" / "synthesis" / "graph" / "full_dag.json"
SCHEMA_PATH = ROOT / "persona" / "schema" / "dimensions.json"
HTML_PATH = ROOT / "persona" / "synthesis" / "visualization" / "full_dag_overview.html"


class _GraphDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_graph_data = False
        self._chunks: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attr_map = dict(attrs)
        if tag == "script" and attr_map.get("id") == "graph-data":
            self._in_graph_data = True

    def handle_data(self, data: str) -> None:
        if self._in_graph_data:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_graph_data:
            self._in_graph_data = False

    def payload(self) -> dict[str, Any]:
        if not self._chunks:
            msg = "visualization graph-data script was not found"
            raise AssertionError(msg)
        return json.loads("".join(self._chunks))


def _graph_data_payload() -> dict[str, Any]:
    parser = _GraphDataParser()
    parser.feed(HTML_PATH.read_text(encoding="utf-8"))
    return parser.payload()


def test_schema_value_domains_match_emitted_graph_nodes() -> None:
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    graph_values = {
        node["id"]: node["values"]
        for node in graph["nodes"]
        if node.get("emit", True) is not False
    }
    schema_values = {
        dimension["id"]: dimension["values"]
        for dimension in schema["dimensions"]
    }

    assert schema_values == graph_values


def test_visualization_distinguishes_schema_attributes_from_helper_nodes() -> None:
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    html = HTML_PATH.read_text(encoding="utf-8")
    payload = _graph_data_payload()

    schema_ids = {dimension["id"] for dimension in schema["dimensions"]}
    graph_ids = {node["id"] for node in graph["nodes"]}
    emitted_ids = {
        node["id"] for node in graph["nodes"] if node.get("emit", True) is not False
    }
    # The renderer counts a node as an attribute when it is emitted or listed
    # in the persona schema; everything else is a latent/helper node.
    attribute_ids = emitted_ids | (schema_ids & graph_ids)

    # v4.4 full DAG: 1,290 emitted persona attributes plus 18 internal helpers.
    assert len(graph_ids) == 1308
    assert len(emitted_ids) == 1290
    assert len(graph_ids - attribute_ids) == 18

    assert payload["counts"] == {
        "schema_attributes": len(attribute_ids),
        "emitted_attributes": len(attribute_ids & emitted_ids),
        "hidden_schema_attributes": len(attribute_ids - emitted_ids),
        "latent_helper_nodes": len(graph_ids - attribute_ids),
        "graph_nodes": len(graph_ids),
        "hidden_graph_nodes": len(graph_ids - emitted_ids),
    }
    assert len(payload["nodes"]) == 1308
    assert len(payload["edges"]) == 6999
    assert sum(category["attributeCount"] for category in payload["categories"]) == len(attribute_ids)
    assert sum(category["helperCount"] for category in payload["categories"]) == 18

    helper_nodes = {node["id"] for node in payload["nodes"] if not node["isAttribute"]}
    assert helper_nodes == graph_ids - attribute_ids
    assert all(node["type"] == "latent/helper" for node in payload["nodes"] if not node["isAttribute"])
    assert {node["id"] for node in payload["nodes"] if node["emit"]} == emitted_ids

    assert "Persona attributes" in html
    assert "Latent/helper nodes" in html
    assert "Graph nodes" in html
