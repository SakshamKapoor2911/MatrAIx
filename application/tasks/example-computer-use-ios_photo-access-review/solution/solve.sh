#!/usr/bin/env bash
set -euo pipefail

mkdir -p /tmp/personabench-ios-photo-access-review

cat > /tmp/personabench-ios-photo-access-review/decision.json <<'EOF'
{
  "app_reviewed": "Photos",
  "photo_access_level": "selected_photos",
  "reason": "I only want this app to see the few images I choose on purpose instead of my full library."
}
EOF
