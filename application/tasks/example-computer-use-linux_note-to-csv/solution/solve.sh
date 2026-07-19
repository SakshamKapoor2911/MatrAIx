#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="${PLAYGROUND_OUTPUT_DIR:-${MATRIX_OUTPUT_DIR:-/app/output}}"
mkdir -p "$OUTPUT_DIR"

cat > "$OUTPUT_DIR/cleaned_list.csv" <<'EOF'
item,quantity,priority
oat milk,2,urgent
batteries,4,normal
trash bags,1,low
EOF

cat > "$OUTPUT_DIR/submission.json" <<'EOF'
{
  "output_file": "/app/output/cleaned_list.csv",
  "rows_written": 3,
  "format": "csv",
  "reason": "CSV keeps the shopping note compact and easy to sort later in a spreadsheet."
}
EOF
