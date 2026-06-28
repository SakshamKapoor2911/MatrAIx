from __future__ import annotations

import json
import tempfile
from html import escape
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from backend.service.local_survey_eval import persona_system_prompt
from backend.service.web_types import (
    WebEvalConfig,
    WebEvalResult,
    WebEvalResultArtifact,
    WebEvalTask,
    WebTrace,
)
from persona_eval.model_client import build_json_client
from persona_eval.types import Persona


def build_web_task_prompt(
    task: WebEvalTask, products: Optional[List[Dict[str, Any]]] = None
) -> str:
    lines = [
        "You are evaluating a website as a realistic user.",
        "Website: {}".format(task.site_name),
        "Website URL: {}".format(task.site_url),
        "Task context: {}".format(task.description),
    ]
    if products:
        lines.append("")
        lines.append(
            "Product catalog (pick selected_product_id from these exact ids):"
        )
        for product in products:
            product_id = str(product.get("id") or "").strip()
            if not product_id:
                continue
            name = str(product.get("name") or product_id)
            category = str(product.get("category") or "")
            price = product.get("price_usd")
            price_str = " | ${}".format(price) if price not in (None, "") else ""
            lines.append(
                "- {} | {} | {}{}".format(product_id, name, category, price_str)
            )
    lines.extend(
        [
            "",
            "Based on your assigned persona, decide a realistic closed-loop goal for this website.",
            "For an ecommerce site, this should usually mean finding and choosing a product that fits your needs.",
            "Describe the steps you would take on the site and then complete the post-interaction form.",
        ]
    )
    if products:
        lines.append(
            "selected_product_id and selected_product_name MUST be one of the catalog products listed above."
        )
    lines.extend(
        [
            "",
            "Return strict JSON with this shape:",
        ]
    )
    return "\n".join(
        lines
        + [
            json.dumps(
                {
                    "goal": "<the website task you decided to perform>",
                    "steps": [
                        {
                            "message": "<what you looked at or did>",
                            "actions": [
                                {"name": "search|click|compare|select|scroll", "arguments": {}}
                            ],
                        }
                    ],
                    "selected_product_id": "<product id or local:selected>",
                    "selected_product_name": "<product or outcome name>",
                    "need_satisfaction": 1,
                    "ease_of_use": 1,
                    "information_quality": 1,
                    "overall_quality": 1,
                    "reason": "<why the website experience did or did not work>",
                },
                indent=2,
            ),
            "Ratings must be integers from 1 to 10.",
        ]
    )


class LocalWebEvalRunner:
    """Run a lightweight website UX simulation through the local runtime."""

    def __call__(
        self,
        persona: Persona,
        task: WebEvalTask,
        config: Optional[WebEvalConfig] = None,
        *,
        created_at: str,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> WebEvalResult:
        config = config or WebEvalConfig()

        def emit(event: Dict[str, Any]) -> None:
            if on_event is not None:
                on_event(event)

        persona_prompt = persona_system_prompt(persona)
        products = _load_task_products(task)
        task_prompt = build_web_task_prompt(task, products)
        prompts = {
            "personaPrompt": persona_prompt,
            "harborPrompt": persona_prompt,
            "taskPrompt": task_prompt,
        }
        emit({"type": "prompts", "prompts": prompts})
        emit({"type": "phase", "phase": "web_simulating"})

        client = build_json_client(config.persona_model)
        raw = client.complete_json(persona_prompt, task_prompt)
        trace = _trace_from_model(raw, task=task, products=products)
        result = WebEvalResult(
            config=config,
            persona=persona,
            task=task,
            web_result=WebEvalResultArtifact.from_dict(raw, created_at=created_at),
            trace=trace,
            created_at=created_at,
            prompts=prompts,
        )
        emit({"type": "done", "result": result.to_dict()})
        return result


def _trace_from_model(
    raw: Dict[str, Any], *, task: WebEvalTask, products: List[Dict[str, Any]]
) -> WebTrace:
    events = []
    goal = str(raw.get("goal") or "Use the website to complete a realistic task.")
    steps = raw.get("steps")
    if not isinstance(steps, list) or not steps:
        steps = [{"message": goal, "actions": [{"name": "observe", "arguments": {}}]}]
    screenshots_dir = Path(tempfile.mkdtemp(prefix="personaeval_web_trace_"))
    selected_product_id = str(
        raw.get("selected_product_id") or raw.get("selectedProductId") or ""
    ).strip()
    for index, step in enumerate(steps, start=1):
        step = step if isinstance(step, dict) else {"message": str(step)}
        actions = step.get("actions")
        if not isinstance(actions, list):
            actions = []
        normalized_actions = []
        for action in actions:
            if isinstance(action, dict):
                normalized_actions.append(
                    {
                        "name": str(action.get("name") or "action"),
                        "arguments": dict(action.get("arguments") or {}),
                    }
                )
        event = {
            "step": index,
            "source": "persona",
            "message": str(step.get("message") or ""),
            "actions": normalized_actions,
            "screenshotFile": "screenshot_{:03d}.svg".format(index),
        }
        _write_svg_screenshot(
            screenshots_dir / event["screenshotFile"],
            task=task,
            step=index,
            event=event,
            products=products,
            selected_product_id=selected_product_id,
        )
        events.append(event)
    return WebTrace(events=events, raw={"goal": goal, "model": raw}, screenshots_dir=screenshots_dir)


def _load_task_products(task: WebEvalTask) -> list[Dict[str, Any]]:
    catalog_path = task.task_path / "environment" / "ecommerce-web" / "site" / "catalog.json"
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    products = payload.get("products") if isinstance(payload, dict) else None
    if not isinstance(products, list) or not products:
        return [
            {
                "id": "desk-001",
                "name": "ModDesk Compact",
                "category": "Home office",
                "price_usd": 249,
                "rating": 4.3,
                "summary": "A compact desk for small spaces and budget-conscious shoppers.",
                "best_for": ["small apartments", "simple setup"],
            },
            {
                "id": "desk-002",
                "name": "FocusDesk Pro",
                "category": "Home office",
                "price_usd": 429,
                "rating": 4.8,
                "summary": "A durable adjustable desk with storage and cable routing.",
                "best_for": ["remote workers", "durability"],
            },
            {
                "id": "lamp-001",
                "name": "LumaBar Desk Lamp",
                "category": "Lighting",
                "price_usd": 74,
                "rating": 4.6,
                "summary": "A dimmable LED desk lamp with warm and cool color modes.",
                "best_for": ["evening reading", "compact desks"],
            },
        ]
    return [product for product in products if isinstance(product, dict)]


def _write_svg_screenshot(
    path: Path,
    *,
    task: WebEvalTask,
    step: int,
    event: Dict[str, Any],
    products: list[Dict[str, Any]],
    selected_product_id: str,
) -> None:
    cards = []
    for idx, product in enumerate(products[:4]):
        x = 36 + idx * 279
        product_id = str(product.get("id") or "item")
        selected = bool(selected_product_id and product_id == selected_product_id)
        cards.append(
            _product_card_svg(
                x=x,
                y=258,
                product=product,
                selected=selected,
            )
        )
    message = str(event.get("message") or "")
    action_labels = []
    for action in event.get("actions") or []:
        if not isinstance(action, dict):
            continue
        name = str(action.get("name") or "action")
        args = action.get("arguments")
        suffix = ""
        if isinstance(args, dict) and args:
            suffix = " " + ", ".join(
                "{}={}".format(str(key), str(value)) for key, value in list(args.items())[:2]
            )
        action_labels.append("{}{}".format(name, suffix))
    action_text = " | ".join(action_labels) if action_labels else "observe"
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760">
  <rect width="1200" height="760" fill="#f6f3ef"/>
  <rect width="1200" height="132" fill="#12343b"/>
  <text x="44" y="58" font-family="Inter, Arial, sans-serif" font-size="34" font-weight="700" fill="#ffffff">{site_name}</text>
  <text x="44" y="92" font-family="Inter, Arial, sans-serif" font-size="17" fill="#d8e7e9">{site_desc}</text>
  <rect x="36" y="164" width="732" height="54" rx="8" fill="#ffffff" stroke="#c7c0b8"/>
  <text x="58" y="198" font-family="Inter, Arial, sans-serif" font-size="16" fill="#66706b">Search by name or need</text>
  <rect x="792" y="164" width="258" height="54" rx="8" fill="#ffffff" stroke="#c7c0b8"/>
  <text x="814" y="198" font-family="Inter, Arial, sans-serif" font-size="16" fill="#66706b">All categories</text>
  <text x="36" y="244" font-family="Inter, Arial, sans-serif" font-size="16" font-weight="700" fill="#222222">Product catalog</text>
  {cards}
  <rect x="36" y="626" width="1128" height="88" rx="10" fill="#ffffff" stroke="#d6cec5"/>
  <text x="60" y="657" font-family="Inter, Arial, sans-serif" font-size="15" font-weight="700" fill="#12343b">Trace step {step}: {action_text}</text>
  <text x="60" y="686" font-family="Inter, Arial, sans-serif" font-size="14" fill="#334155">{message}</text>
</svg>
""".format(
        site_name=_svg_text(task.site_name),
        site_desc=_svg_text(task.description),
        cards="\n  ".join(cards),
        step=step,
        action_text=_svg_text(_truncate(action_text, 110)),
        message=_svg_text(_truncate(message, 150)),
    )
    path.write_text(svg, encoding="utf-8")


def _product_card_svg(
    *,
    x: int,
    y: int,
    product: Dict[str, Any],
    selected: bool,
) -> str:
    product_id = str(product.get("id") or "item")
    name = str(product.get("name") or product_id)
    category = str(product.get("category") or "Product")
    price = str(product.get("price_usd") or "")
    rating = str(product.get("rating") or "")
    summary = str(product.get("summary") or "")
    best_for = product.get("best_for")
    tags = ", ".join(str(tag) for tag in best_for[:2]) if isinstance(best_for, list) else ""
    border = "#1d5f53" if selected else "#d6cec5"
    badge = (
        '<rect x="{bx}" y="{by}" width="74" height="24" rx="12" fill="#dff4ec"/>'
        '<text x="{tx}" y="{ty}" font-family="Inter, Arial, sans-serif" font-size="12" font-weight="700" fill="#1d5f53">selected</text>'
    ).format(bx=x + 166, by=y + 18, tx=x + 181, ty=y + 35) if selected else ""
    return """<g>
    <rect x="{x}" y="{y}" width="252" height="330" rx="10" fill="#ffffff" stroke="{border}" stroke-width="{stroke}"/>
    <rect x="{media_x}" y="{media_y}" width="252" height="112" rx="10" fill="#ece5dc"/>
    <rect x="{media_x}" y="{media_bottom}" width="252" height="20" fill="#ece5dc"/>
    <text x="{body_x}" y="{id_y}" font-family="Inter, Arial, sans-serif" font-size="12" fill="#66706b">{product_id}</text>
    {badge}
    <text x="{body_x}" y="{name_y}" font-family="Inter, Arial, sans-serif" font-size="21" font-weight="700" fill="#222222">{name}</text>
    <text x="{body_x}" y="{cat_y}" font-family="Inter, Arial, sans-serif" font-size="13" fill="#66706b">{category}</text>
    <text x="{body_x}" y="{price_y}" font-family="Inter, Arial, sans-serif" font-size="22" font-weight="700" fill="#1d5f53">${price}</text>
    <text x="{rating_x}" y="{price_y}" font-family="Inter, Arial, sans-serif" font-size="14" fill="#6b4f00">Rating {rating}/5</text>
    <text x="{body_x}" y="{summary_y}" font-family="Inter, Arial, sans-serif" font-size="13" fill="#334155">{summary}</text>
    <text x="{body_x}" y="{tags_y}" font-family="Inter, Arial, sans-serif" font-size="12" fill="#20443d">{tags}</text>
  </g>""".format(
        x=x,
        y=y,
        media_x=x,
        media_y=y,
        media_bottom=y + 92,
        body_x=x + 18,
        id_y=y + 142,
        name_y=y + 175,
        cat_y=y + 199,
        price_y=y + 236,
        rating_x=x + 114,
        summary_y=y + 272,
        tags_y=y + 306,
        product_id=_svg_text(_truncate(product_id, 26)),
        name=_svg_text(_truncate(name, 20)),
        category=_svg_text(_truncate(category, 28)),
        price=_svg_text(price),
        rating=_svg_text(rating),
        summary=_svg_text(_truncate(summary, 58)),
        tags=_svg_text(_truncate(tags, 44)),
        border=border,
        stroke=3 if selected else 1,
        badge=badge,
    )


def _truncate(value: str, limit: int) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _svg_text(value: str) -> str:
    return escape(str(value), quote=True)
