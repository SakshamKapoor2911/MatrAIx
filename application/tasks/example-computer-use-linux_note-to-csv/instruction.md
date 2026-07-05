# Note to CSV cleanup (Linux)

You are setting up a new Linux desktop and want a quick structured copy of a
rough shopping note.

Turn this rough note into a CSV table:

- oat milk | 2 | urgent
- batteries | 4 | normal
- trash bags | 1 | low

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
