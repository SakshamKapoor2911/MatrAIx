#!/usr/bin/env bash
set -euo pipefail

mkdir -p /tmp/matraix-ios-notification-preferences

cat > /tmp/matraix-ios-notification-preferences/decision.json <<'EOF'
{
  "keep_notifications_on": false,
  "app_reviewed": "Messages",
  "reason": "I mute group chats during work hours but still want direct messages to break through with banners."
}
EOF
