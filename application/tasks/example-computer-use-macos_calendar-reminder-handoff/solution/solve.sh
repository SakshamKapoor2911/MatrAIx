#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="${PLAYGROUND_OUTPUT_DIR:-${MATRIX_OUTPUT_DIR:-/app/output}}"
mkdir -p "$OUTPUT_DIR"

cat > "$OUTPUT_DIR/handoff.txt" <<'EOF'
Calendar: Dentist follow-up | 2026-08-14 09:30 | North Clinic
Reminder: Bring insurance card
EOF

cat > "$OUTPUT_DIR/plan.json" <<'EOF'
{
  "calendar_event_title": "Dentist follow-up",
  "reminder_title": "Bring insurance card",
  "location": "North Clinic",
  "reason": "The appointment belongs on the calendar because it is time-based, while the item to bring works better as a reminder."
}
EOF
