#!/usr/bin/env bash
set -euo pipefail

mkdir -p /tmp/matraix-linux-notification-preferences

cat > /tmp/matraix-linux-notification-preferences/decision.json <<'EOF'
{
  "keep_notifications_on": false,
  "app_reviewed": "Notify OSD",
  "reason": "I keep notifications off while focusing and only allow them for calendar and messaging apps."
}
EOF
