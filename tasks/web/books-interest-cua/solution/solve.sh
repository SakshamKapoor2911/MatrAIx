#!/usr/bin/env bash
set -euo pipefail

output_dir="/app/output"
if [ "$(uname -s)" = "Darwin" ]; then
  output_dir="/Users/lume/output"
fi
mkdir -p "$output_dir"

cat > "${output_dir}/book_interest.json" <<'EOF'
{
  "title": "A Light in the Attic",
  "price_gbp": "£51.77",
  "interested": true,
  "reason": "I would consider this poetry collection at this price after browsing the catalog in the browser."
}
EOF
