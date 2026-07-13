# Calendar + reminder handoff (macOS)

Read the scenario brief in `input/context.md`, then set up a small Calendar and Reminders handoff.

Create `/tmp/personabench-macos-calendar-reminder-handoff/handoff.txt` with
exactly these two lines:

```text
Calendar: Dentist follow-up | 2026-08-14 09:30 | North Clinic
Reminder: Bring insurance card
```

Then save `/tmp/personabench-macos-calendar-reminder-handoff/plan.json`:

```json
{
  "calendar_event_title": "Dentist follow-up",
  "reminder_title": "Bring insurance card",
  "location": "North Clinic",
  "reason": "<why this belongs across Calendar and Reminders>"
}
```

Do not add extra lines to `handoff.txt`.
