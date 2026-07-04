#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

cat > /app/output/book_interest.json <<'EOF'
{
  "decision_subject_id": "a-light-in-the-attic",
  "decision_subject_label": "A Light in the Attic",
  "decision_outcome": "selected",
  "basis_primary": "taste",
  "exploration_style": "quick_pick",
  "reason": "I would realistically start with this poetry collection because the title catches my interest and the price still feels within reach.",
  "task_price_text": "£51.77"
}
EOF
