#!/usr/bin/env bash
set -euo pipefail

mkdir -p /tmp/personabench-macos-calendar-reminder-handoff

cat > /tmp/personabench-macos-calendar-reminder-handoff/handoff.txt <<'EOF'
Calendar: Dentist follow-up | 2026-08-14 09:30 | North Clinic
Reminder: Bring insurance card
EOF

cat > /tmp/personabench-macos-calendar-reminder-handoff/plan.json <<'EOF'
{
  "calendar_event_title": "Dentist follow-up",
  "reminder_title": "Bring insurance card",
  "location": "North Clinic",
  "reason": "The appointment belongs on the calendar because it is time-based, while the item to bring works better as a reminder."
}
EOF
