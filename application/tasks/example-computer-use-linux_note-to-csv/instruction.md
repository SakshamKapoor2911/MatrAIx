# Note to CSV cleanup (Linux)

Read the scenario brief in `input/context.md`, then clean a short note into a CSV.

Create `/tmp/personabench-linux-note-to-csv/cleaned_list.csv` with this exact
header:

```text
item,quantity,priority
```

Then save `/tmp/personabench-linux-note-to-csv/submission.json`:

```json
{
  "output_file": "/tmp/personabench-linux-note-to-csv/cleaned_list.csv",
  "rows_written": 3,
  "format": "csv",
  "reason": "<why you chose this structure>"
}
```

Rules:

- `format` must be exactly `csv`
- `rows_written` must be `3`
- do not add extra columns or extra data rows
