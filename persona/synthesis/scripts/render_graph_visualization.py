#!/usr/bin/env python3
"""Render an interactive HTML visualization of the Persona Full DAG."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from persona.synthesis.sampler import DEFAULT_GRAPH_PATH, graph_summary, load_graph  # noqa: E402

DEFAULT_SCHEMA_PATH = REPO_ROOT / "persona" / "schema" / "dimensions.json"

PALETTE = [
    "#2563eb",
    "#16a34a",
    "#dc2626",
    "#9333ea",
    "#ca8a04",
    "#0891b2",
    "#db2777",
    "#4f46e5",
    "#059669",
    "#ea580c",
    "#7c3aed",
    "#0f766e",
    "#be123c",
    "#65a30d",
    "#0284c7",
    "#a21caf",
    "#b45309",
    "#047857",
    "#4338ca",
    "#c2410c",
]


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _category(node: dict[str, Any]) -> str:
    return node.get("category") or "Uncategorized"


def _load_schema_attribute_ids(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    schema = json.loads(path.read_text(encoding="utf-8"))
    return {dimension["id"] for dimension in schema.get("dimensions", [])}


def _is_attribute(node: dict[str, Any], schema_attribute_ids: set[str]) -> bool:
    if node.get("emit", True) is not False:
        return True
    return node["id"] in schema_attribute_ids


def _count_nodes(graph: dict[str, Any], schema_attribute_ids: set[str]) -> dict[str, int]:
    nodes = graph.get("nodes", [])
    node_ids = {node["id"] for node in nodes}
    emitted_ids = {
        node["id"] for node in nodes if node.get("emit", True) is not False
    }
    schema_ids = schema_attribute_ids & node_ids
    attribute_ids = emitted_ids | schema_ids
    hidden_graph_ids = node_ids - emitted_ids
    hidden_attribute_ids = attribute_ids & hidden_graph_ids
    helper_ids = node_ids - attribute_ids

    return {
        "schema_attributes": len(attribute_ids),
        "emitted_attributes": len(attribute_ids & emitted_ids),
        "hidden_schema_attributes": len(hidden_attribute_ids),
        "latent_helper_nodes": len(helper_ids),
        "graph_nodes": len(node_ids),
        "hidden_graph_nodes": len(hidden_graph_ids),
    }


def _stable_jitter(node_id: str) -> float:
    digest = hashlib.sha1(node_id.encode("utf-8")).hexdigest()
    return (int(digest[:8], 16) % 1000) / 999 - 0.5


def _layout_payload(
    graph: dict[str, Any], schema_attribute_ids: set[str]
) -> dict[str, Any]:
    nodes = graph.get("nodes", [])
    edges = graph.get("directed_proposal_edges", [])
    order = graph.get("proposal_view", {}).get("topological_order", [])
    topo = {node_id: i for i, node_id in enumerate(order)}
    in_degree = Counter(edge.get("target") for edge in edges)
    out_degree = Counter(edge.get("source") for edge in edges)

    categories = Counter(_category(node) for node in nodes)
    avg_topo = {}
    for category in categories:
        positions = [
            topo[node["id"]]
            for node in nodes
            if _category(node) == category and node["id"] in topo
        ]
        avg_topo[category] = sum(positions) / len(positions) if positions else 0
    category_order = sorted(categories, key=lambda cat: (avg_topo[cat], cat))
    category_index = {category: i for i, category in enumerate(category_order)}

    width = 4300
    lane_height = 72
    top_pad = 110
    bottom_pad = 110
    height = top_pad + bottom_pad + lane_height * len(category_order)
    x_min = 150
    x_max = width - 90
    denom = max(1, len(order) - 1)

    node_payload = []
    sorted_nodes = sorted(nodes, key=lambda node: (topo.get(node["id"], 10**9), node["id"]))
    for node in sorted_nodes:
        node_id = node["id"]
        category = _category(node)
        lane = category_index[category]
        pos = topo.get(node_id, len(topo))
        x = x_min + (pos / denom) * (x_max - x_min)
        y = top_pad + lane * lane_height + lane_height / 2 + _stable_jitter(node_id) * 34
        incoming = in_degree[node_id]
        outgoing = out_degree[node_id]
        is_attribute = _is_attribute(node, schema_attribute_ids)
        node_payload.append(
            {
                "id": node_id,
                "label": node.get("label", node_id),
                "category": category,
                "categoryIndex": lane,
                "type": "attribute" if is_attribute else "latent/helper",
                "isAttribute": is_attribute,
                "x": round(x, 2),
                "y": round(y, 2),
                "degree": incoming + outgoing,
                "in": incoming,
                "out": outgoing,
                "values": len(node.get("values", [])),
                "emit": node.get("emit", True) is not False,
            }
        )

    payload_index = {node["id"]: i for i, node in enumerate(node_payload)}
    edge_payload = []
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source in payload_index and target in payload_index:
            edge_payload.append(
                [
                    payload_index[source],
                    payload_index[target],
                    round(float(edge.get("edge_weight", 1.0)), 4),
                ]
            )

    attribute_categories = Counter(
        node["category"] for node in node_payload if node["isAttribute"]
    )
    helper_categories = Counter(
        node["category"] for node in node_payload if not node["isAttribute"]
    )
    category_payload = [
        {
            "name": category,
            "count": categories[category],
            "attributeCount": attribute_categories[category],
            "helperCount": helper_categories[category],
            "color": PALETTE[i % len(PALETTE)],
            "y": round(top_pad + i * lane_height + lane_height / 2, 2),
        }
        for i, category in enumerate(category_order)
    ]

    return {
        "width": width,
        "height": height,
        "nodes": node_payload,
        "edges": edge_payload,
        "categories": category_payload,
        "counts": _count_nodes(graph, schema_attribute_ids),
        "maxDegree": max((node["degree"] for node in node_payload), default=1),
    }


def _top_nodes(payload: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    return sorted(
        payload["nodes"],
        key=lambda node: (-node["degree"], node["id"]),
    )[:limit]


def _category_table(
    graph: dict[str, Any], schema_attribute_ids: set[str]
) -> list[dict[str, Any]]:
    nodes = graph.get("nodes", [])
    edges = graph.get("directed_proposal_edges", [])
    by_id = {node["id"]: node for node in nodes}
    rows: dict[str, dict[str, Any]] = {}
    for node in nodes:
        category = _category(node)
        row = rows.setdefault(
            category,
            {
                "category": category,
                "nodes": 0,
                "attributes": 0,
                "emitted": 0,
                "hidden_attributes": 0,
                "helpers": 0,
                "incoming": 0,
                "outgoing": 0,
            },
        )
        is_attribute = _is_attribute(node, schema_attribute_ids)
        row["nodes"] += 1
        if is_attribute:
            row["attributes"] += 1
        else:
            row["helpers"] += 1
        if is_attribute and node.get("emit", True) is not False:
            row["emitted"] += 1
        if is_attribute and node.get("emit", True) is False:
            row["hidden_attributes"] += 1
    for edge in edges:
        source = by_id.get(edge.get("source"))
        target = by_id.get(edge.get("target"))
        if source:
            rows[_category(source)]["outgoing"] += 1
        if target:
            rows[_category(target)]["incoming"] += 1
    return sorted(rows.values(), key=lambda row: (-row["nodes"], row["category"]))


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body = []
    for row in rows:
        body.append(
            "<tr>"
            + "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row)
            + "</tr>"
        )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _json_script(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def render_html(
    graph: dict[str, Any],
    *,
    graph_path: Path,
    schema_path: Path | None,
    top_nodes: int,
) -> str:
    summary = graph_summary(graph)
    schema_attribute_ids = _load_schema_attribute_ids(schema_path)
    payload = _layout_payload(graph, schema_attribute_ids)
    counts = payload["counts"]
    categories = _category_table(graph, schema_attribute_ids)
    top = _top_nodes(payload, top_nodes)
    graph_label = _display_path(graph_path)

    category_options = "\n".join(
        f'<option value="{html.escape(row["name"])}">{html.escape(row["name"])} '
        f'({row["attributeCount"]} attrs, {row["helperCount"]} helper)</option>'
        for row in payload["categories"]
    )
    category_rows = [
        [
            row["category"],
            f"{row['nodes']:,}",
            f"{row['attributes']:,}",
            f"{row['emitted']:,}",
            f"{row['hidden_attributes']:,}",
            f"{row['helpers']:,}",
            f"{row['incoming']:,}",
            f"{row['outgoing']:,}",
        ]
        for row in categories
    ]
    top_rows = [
        [
            row["id"],
            row["label"],
            row["category"],
            row["type"],
            row["degree"],
            row["in"],
            row["out"],
            row["values"],
            "yes" if row["isAttribute"] and row["emit"] else "no",
        ]
        for row in top
    ]

    summary_cards = [
        ("Persona attributes", f"{counts['schema_attributes']:,}"),
        ("Emitted attributes", f"{counts['emitted_attributes']:,}"),
        ("Hidden attributes", f"{counts['hidden_schema_attributes']:,}"),
        ("Latent/helper nodes", f"{counts['latent_helper_nodes']:,}"),
        ("Graph nodes", f"{summary['nodes']:,}"),
        ("Directed edges", f"{summary['directed_edges']:,}"),
        ("Full CPTs", f"{summary['full_cpts']:,}"),
        ("Masks", f"{summary['conditional_masks']:,}"),
    ]
    cards = "".join(
        f'<section class="card"><div class="metric">{html.escape(value)}</div>'
        f'<div class="label">{html.escape(label)}</div></section>'
        for label, value in summary_cards
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>Persona Full DAG Graph Visualization</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #1f2933;
      --muted: #627184;
      --line: #d7dee8;
      --panel: #f7f9fb;
      --panel-strong: #eef3f8;
      --accent: #1864ab;
      --danger: #b42318;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: #ffffff;
    }}
    main {{
      max-width: 1460px;
      margin: 0 auto;
      padding: 28px 24px 48px;
    }}
    h1 {{ margin: 0 0 8px; font-size: 30px; font-weight: 720; }}
    h2 {{ margin: 32px 0 12px; font-size: 20px; }}
    p {{ color: var(--muted); line-height: 1.5; margin: 8px 0 0; }}
    code {{
      background: var(--panel-strong);
      border-radius: 4px;
      padding: 1px 4px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
      margin: 22px 0;
    }}
    .card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px 14px;
      background: var(--panel);
      min-height: 74px;
    }}
    .metric {{ font-size: 22px; font-weight: 720; color: var(--accent); }}
    .label {{ margin-top: 4px; font-size: 12px; color: var(--muted); }}
    .graph-shell {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 310px;
      gap: 12px;
      align-items: stretch;
      margin-top: 18px;
    }}
    .graph-panel {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfe;
      min-height: 720px;
      overflow: hidden;
      position: relative;
    }}
    .toolbar {{
      display: grid;
      grid-template-columns: minmax(180px, 1.3fr) minmax(160px, 1fr) 160px 120px 110px 100px;
      gap: 8px;
      padding: 10px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
      align-items: center;
    }}
    .toolbar input[type="search"],
    .toolbar select {{
      width: 100%;
      height: 34px;
      border: 1px solid #bac5d3;
      border-radius: 6px;
      padding: 0 10px;
      font: inherit;
      color: var(--ink);
      background: #ffffff;
    }}
    .toolbar label {{
      font-size: 12px;
      color: var(--muted);
      display: flex;
      gap: 6px;
      align-items: center;
      white-space: nowrap;
    }}
    .toolbar input[type="range"] {{
      width: 92px;
    }}
    button {{
      height: 34px;
      border: 1px solid #aeb9c8;
      border-radius: 6px;
      background: #ffffff;
      color: var(--ink);
      font: inherit;
      cursor: pointer;
    }}
    button:hover {{ background: var(--panel-strong); }}
    canvas {{
      width: 100%;
      height: 660px;
      display: block;
      cursor: grab;
      background: #fbfcfe;
    }}
    canvas.dragging {{ cursor: grabbing; }}
    .status {{
      position: absolute;
      left: 12px;
      bottom: 10px;
      padding: 6px 8px;
      border: 1px solid rgba(125, 135, 151, 0.35);
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.88);
      color: var(--muted);
      font-size: 12px;
      pointer-events: none;
    }}
    .inspector {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
      padding: 14px;
      min-height: 720px;
    }}
    .inspector h3 {{
      margin: 0 0 8px;
      font-size: 15px;
    }}
    .inspector dl {{
      display: grid;
      grid-template-columns: 82px minmax(0, 1fr);
      gap: 8px 10px;
      margin: 14px 0 0;
      font-size: 13px;
    }}
    .inspector dt {{
      color: var(--muted);
    }}
    .inspector dd {{
      margin: 0;
      overflow-wrap: anywhere;
    }}
    .legend {{
      display: grid;
      gap: 5px;
      max-height: 360px;
      overflow: auto;
      margin-top: 16px;
      border-top: 1px solid var(--line);
      padding-top: 12px;
    }}
    .legend-item {{
      display: grid;
      grid-template-columns: 12px minmax(0, 1fr) auto;
      gap: 8px;
      align-items: center;
      font-size: 12px;
      color: var(--muted);
    }}
    .swatch {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
      display: inline-block;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      border: 1px solid var(--line);
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: var(--panel-strong);
      font-weight: 680;
      color: #2c3a4b;
    }}
    tr:nth-child(even) td {{ background: #fafbfd; }}
    @media (max-width: 980px) {{
      main {{ padding: 20px 14px 36px; }}
      .graph-shell {{ grid-template-columns: 1fr; }}
      .toolbar {{ grid-template-columns: 1fr 1fr; }}
      canvas {{ height: 560px; }}
      .inspector {{ min-height: 0; }}
    }}
  </style>
</head>
<body>
<main>
  <h1>Persona Full DAG Graph Visualization</h1>
  <p>
    Generated from <code>{html.escape(graph_label)}</code>. The main canvas
    draws all {counts['graph_nodes']:,} graph nodes and
    {summary['directed_edges']:,} directed proposal edges. The graph contains
    {counts['schema_attributes']:,} persona attributes plus
    {counts['latent_helper_nodes']:,} latent/helper nodes; default samples emit
    {counts['emitted_attributes']:,} attributes and hide
    {counts['hidden_schema_attributes']:,} persona attributes marked
    <code>emit:false</code>. X position follows
    <code>proposal_view.topological_order</code>; Y position groups nodes into
    category lanes.
  </p>
  <div class="cards">{cards}</div>

  <section class="graph-shell" aria-label="Interactive full DAG graph">
    <div class="graph-panel">
      <div class="toolbar">
        <input id="search" type="search" placeholder="Search node id, label, or category">
        <select id="category">
          <option value="">All categories</option>
          {category_options}
        </select>
        <label>Min degree <input id="degree" type="range" min="0" max="{payload['maxDegree']}" value="0"><span id="degreeValue">0</span></label>
        <label><input id="hidden" type="checkbox" checked> hidden/helper</label>
        <label><input id="edges" type="checkbox" checked> edges</label>
        <button id="reset" type="button">Reset</button>
      </div>
      <canvas id="graph"></canvas>
      <div id="status" class="status">Loading graph...</div>
    </div>
    <aside class="inspector">
      <h3 id="nodeTitle">No node selected</h3>
      <p id="nodeHint">Hover or click a node to inspect its fields. Drag to pan; scroll to zoom.</p>
      <dl id="nodeDetails"></dl>
      <div class="legend" id="legend"></div>
    </aside>
  </section>

  <h2>Highest-Degree Nodes</h2>
  {_table(["Node", "Label", "Category", "Type", "Degree", "In", "Out", "Values", "Emitted attribute"], top_rows)}
  <h2>Category Inventory</h2>
  {_table(["Category", "Graph nodes", "Attributes", "Emitted attributes", "Hidden attributes", "Helper nodes", "Incoming edges", "Outgoing edges"], category_rows)}
</main>

<script id="graph-data" type="application/json">{_json_script(payload)}</script>
<script>
(() => {{
  const data = JSON.parse(document.getElementById("graph-data").textContent);
  const canvas = document.getElementById("graph");
  const ctx = canvas.getContext("2d");
  const search = document.getElementById("search");
  const category = document.getElementById("category");
  const degree = document.getElementById("degree");
  const degreeValue = document.getElementById("degreeValue");
  const hidden = document.getElementById("hidden");
  const edgesToggle = document.getElementById("edges");
  const reset = document.getElementById("reset");
  const status = document.getElementById("status");
  const nodeTitle = document.getElementById("nodeTitle");
  const nodeHint = document.getElementById("nodeHint");
  const nodeDetails = document.getElementById("nodeDetails");
  const legend = document.getElementById("legend");

  const categories = data.categories;
  const colorByCategory = new Map(categories.map((cat) => [cat.name, cat.color]));
  const maxDegree = Math.max(1, data.maxDegree);
  let scale = 1;
  let offsetX = 0;
  let offsetY = 0;
  let dragging = false;
  let dragStart = null;
  let hovered = null;
  let selected = null;
  let visibleNodes = new Set();

  function resize() {{
    const rect = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.floor(rect.width * ratio));
    canvas.height = Math.max(1, Math.floor(rect.height * ratio));
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    draw();
  }}

  function fit() {{
    const rect = canvas.getBoundingClientRect();
    const sx = rect.width / data.width;
    const sy = rect.height / data.height;
    scale = Math.min(sx, sy) * 0.94;
    offsetX = (rect.width - data.width * scale) / 2;
    offsetY = (rect.height - data.height * scale) / 2;
    draw();
  }}

  function screen(node) {{
    return {{ x: node.x * scale + offsetX, y: node.y * scale + offsetY }};
  }}

  function world(x, y) {{
    return {{ x: (x - offsetX) / scale, y: (y - offsetY) / scale }};
  }}

  function nodeRadius(node) {{
    return 2.2 + 6.2 * Math.sqrt(node.degree / maxDegree);
  }}

  function filters() {{
    return {{
      query: search.value.trim().toLowerCase(),
      category: category.value,
      minDegree: Number(degree.value || 0),
      includeHidden: hidden.checked,
    }};
  }}

  function matches(node, f) {{
    if (!f.includeHidden && !node.emit) return false;
    if (f.category && node.category !== f.category) return false;
    if (node.degree < f.minDegree) return false;
    if (f.query) {{
      const haystack = `${{node.id}} ${{node.label}} ${{node.category}} ${{node.type}}`.toLowerCase();
      if (!haystack.includes(f.query)) return false;
    }}
    return true;
  }}

  function computeVisible() {{
    const f = filters();
    visibleNodes = new Set();
    data.nodes.forEach((node, index) => {{
      if (matches(node, f)) visibleNodes.add(index);
    }});
  }}

  function edgeHighlighted(source, target) {{
    return selected !== null && (source === selected || target === selected);
  }}

  function drawLanes() {{
    ctx.save();
    ctx.lineWidth = 1;
    ctx.font = "12px -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
    categories.forEach((cat) => {{
      const y = cat.y * scale + offsetY;
      if (y < -40 || y > canvas.getBoundingClientRect().height + 40) return;
      ctx.strokeStyle = "rgba(151, 163, 179, 0.22)";
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.getBoundingClientRect().width, y);
      ctx.stroke();
      ctx.fillStyle = "rgba(31, 41, 51, 0.70)";
      ctx.fillText(cat.name, 10, y - 8);
    }});
    ctx.restore();
  }}

  function drawEdges() {{
    if (!edgesToggle.checked) return;
    ctx.save();
    ctx.lineCap = "round";
    for (const edge of data.edges) {{
      const sourceIndex = edge[0];
      const targetIndex = edge[1];
      if (!visibleNodes.has(sourceIndex) || !visibleNodes.has(targetIndex)) continue;
      const s = screen(data.nodes[sourceIndex]);
      const t = screen(data.nodes[targetIndex]);
      const highlight = edgeHighlighted(sourceIndex, targetIndex);
      ctx.strokeStyle = highlight ? "rgba(17, 24, 39, 0.42)" : "rgba(89, 103, 124, 0.055)";
      ctx.lineWidth = highlight ? 1.4 : 0.55;
      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      const midX = (s.x + t.x) / 2;
      ctx.bezierCurveTo(midX, s.y, midX, t.y, t.x, t.y);
      ctx.stroke();
    }}
    ctx.restore();
  }}

  function drawNodes() {{
    ctx.save();
    for (let i = 0; i < data.nodes.length; i++) {{
      if (!visibleNodes.has(i)) continue;
      const node = data.nodes[i];
      const p = screen(node);
      const r = nodeRadius(node);
      if (
        p.x < -20 || p.x > canvas.getBoundingClientRect().width + 20 ||
        p.y < -20 || p.y > canvas.getBoundingClientRect().height + 20
      ) continue;
      ctx.globalAlpha = node.emit ? 0.92 : 0.44;
      ctx.fillStyle = colorByCategory.get(node.category) || "#64748b";
      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
      ctx.fill();
      if (i === hovered || i === selected) {{
        ctx.globalAlpha = 1;
        ctx.lineWidth = i === selected ? 2.4 : 1.6;
        ctx.strokeStyle = i === selected ? "#111827" : "#ffffff";
        ctx.stroke();
      }}
    }}
    ctx.restore();
  }}

  function draw() {{
    if (!ctx) return;
    computeVisible();
    const rect = canvas.getBoundingClientRect();
    ctx.clearRect(0, 0, rect.width, rect.height);
    drawLanes();
    drawEdges();
    drawNodes();
    let visibleAttributes = 0;
    for (const index of visibleNodes) {{
      if (data.nodes[index].isAttribute) visibleAttributes += 1;
    }}
    status.textContent =
      `${{visibleNodes.size.toLocaleString()}} / ${{data.nodes.length.toLocaleString()}} graph nodes, ` +
      `${{visibleAttributes.toLocaleString()}} / ${{data.counts.schema_attributes.toLocaleString()}} attributes, ` +
      `${{data.edges.length.toLocaleString()}} edges`;
  }}

  function inspect(index) {{
    if (index === null || index === undefined) {{
      nodeTitle.textContent = "No node selected";
      nodeHint.textContent = "Hover or click a node to inspect its fields. Drag to pan; scroll to zoom.";
      nodeDetails.innerHTML = "";
      return;
    }}
    const node = data.nodes[index];
    nodeTitle.textContent = node.id;
    nodeHint.textContent = node.label;
    nodeDetails.innerHTML = [
      ["Category", node.category],
      ["Type", node.type],
      ["Degree", node.degree],
      ["Incoming", node.in],
      ["Outgoing", node.out],
      ["Values", node.values],
      ["Persona attr", node.isAttribute ? "yes" : "no"],
      ["Emitted", node.isAttribute && node.emit ? "yes" : "no"],
      ["Position", `${{Math.round(node.x)}}, ${{Math.round(node.y)}}`],
    ].map(([key, value]) => `<dt>${{key}}</dt><dd>${{value}}</dd>`).join("");
  }}

  function nearestNode(clientX, clientY) {{
    const rect = canvas.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    let best = null;
    let bestDist = Infinity;
    for (let i = 0; i < data.nodes.length; i++) {{
      if (!visibleNodes.has(i)) continue;
      const p = screen(data.nodes[i]);
      const r = Math.max(8, nodeRadius(data.nodes[i]) + 4);
      const dx = p.x - x;
      const dy = p.y - y;
      const d = dx * dx + dy * dy;
      if (d < r * r && d < bestDist) {{
        best = i;
        bestDist = d;
      }}
    }}
    return best;
  }}

  function renderLegend() {{
    legend.innerHTML = categories.map((cat) => (
      `<div class="legend-item"><span class="swatch" style="background:${{cat.color}}"></span>` +
      `<span>${{cat.name}}</span><span>${{cat.attributeCount}}/${{cat.count}}</span></div>`
    )).join("");
  }}

  canvas.addEventListener("mousemove", (event) => {{
    if (dragging && dragStart) {{
      offsetX = dragStart.offsetX + (event.clientX - dragStart.x);
      offsetY = dragStart.offsetY + (event.clientY - dragStart.y);
      draw();
      return;
    }}
    const next = nearestNode(event.clientX, event.clientY);
    if (next !== hovered) {{
      hovered = next;
      if (selected === null) inspect(hovered);
      draw();
    }}
  }});

  canvas.addEventListener("mouseleave", () => {{
    hovered = null;
    if (selected === null) inspect(null);
    draw();
  }});

  canvas.addEventListener("mousedown", (event) => {{
    dragging = true;
    canvas.classList.add("dragging");
    dragStart = {{ x: event.clientX, y: event.clientY, offsetX, offsetY }};
  }});

  window.addEventListener("mouseup", () => {{
    dragging = false;
    canvas.classList.remove("dragging");
    dragStart = null;
  }});

  canvas.addEventListener("click", (event) => {{
    const next = nearestNode(event.clientX, event.clientY);
    selected = next;
    inspect(selected);
    draw();
  }});

  canvas.addEventListener("wheel", (event) => {{
    event.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const mx = event.clientX - rect.left;
    const my = event.clientY - rect.top;
    const before = world(mx, my);
    const factor = event.deltaY < 0 ? 1.13 : 0.88;
    scale = Math.max(0.08, Math.min(8, scale * factor));
    offsetX = mx - before.x * scale;
    offsetY = my - before.y * scale;
    draw();
  }}, {{ passive: false }});

  [search, category, degree, hidden, edgesToggle].forEach((control) => {{
    control.addEventListener("input", () => {{
      degreeValue.textContent = degree.value;
      selected = null;
      inspect(null);
      draw();
    }});
  }});

  reset.addEventListener("click", () => {{
    search.value = "";
    category.value = "";
    degree.value = "0";
    degreeValue.textContent = "0";
    hidden.checked = true;
    edgesToggle.checked = true;
    selected = null;
    inspect(null);
    fit();
  }});

  renderLegend();
  resize();
  fit();
  window.addEventListener("resize", () => {{
    resize();
    fit();
  }});
}})();
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "persona" / "synthesis" / "visualization" / "full_dag_overview.html",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help="Schema dimensions file used to distinguish attributes from helper nodes.",
    )
    parser.add_argument("--top-nodes", type=int, default=80)
    args = parser.parse_args()

    graph = load_graph(args.graph)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        render_html(
            graph,
            graph_path=args.graph,
            schema_path=args.schema,
            top_nodes=args.top_nodes,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"visualization": str(args.out), "top_nodes": args.top_nodes}, indent=2))


if __name__ == "__main__":
    main()
