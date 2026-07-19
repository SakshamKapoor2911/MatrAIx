#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="${PLAYGROUND_OUTPUT_DIR:-${MATRIX_OUTPUT_DIR:-/app/output}}"
mkdir -p "$OUTPUT_DIR"

cat > "$OUTPUT_DIR/decision.json" <<'EOF'
{
  "app_reviewed": "News",
  "browsed_full_offer": true,
  "reviewed_features_and_pricing": true,
  "clicked_get_started": false,
  "price_seen": "$12.99/month",
  "highlights_noticed": [
    "Hundreds of magazines",
    "Ad-free reading",
    "Apple News+ audio"
  ],
  "reason": "I scrolled the whole offer and came back to the price; Get Started is not worth it because I already pay for a couple of publisher apps."
}
EOF
