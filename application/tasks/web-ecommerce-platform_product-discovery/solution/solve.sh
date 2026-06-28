#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 <<'PY'
import json
from pathlib import Path
from urllib.request import urlopen

with urlopen("http://ecommerce-web:8000/catalog.json", timeout=10) as response:
    catalog = json.load(response)

product = next(item for item in catalog["products"] if item["id"] == "desk-002")
payload = {
    "selected_product_id": product["id"],
    "selected_product_name": product["name"],
    "need_satisfaction": 8,
    "ease_of_use": 7,
    "overall_experience_rating": 8,
    "reason": "The catalog and comparison table made it easy to choose the sturdy desk for a remote-work setup.",
}
Path("/app/output/ecommerce_interaction.json").write_text(json.dumps(payload, indent=2) + "\n")
PY
