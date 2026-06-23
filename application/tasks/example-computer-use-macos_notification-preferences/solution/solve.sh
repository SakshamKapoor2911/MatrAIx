#!/usr/bin/env bash
set -euo pipefail

mkdir -p /tmp/matraix-macos-notification-preferences

cat > /tmp/matraix-macos-notification-preferences/decision.json <<'EOF'
{
  "keep_notifications_on": true,
  "app_reviewed": "Mail",
  "reason": "I want delivery updates for orders but prefer banner style over full-screen alerts."
}
EOF
