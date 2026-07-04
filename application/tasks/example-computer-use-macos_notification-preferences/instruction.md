# Calendar + reminder handoff (macOS)

You are setting up a new Mac and want a clean **cross-app handoff** between a
calendar event and a reminder.

Use this brief:

- Event title: `Dentist follow-up`
- Date: `2026-08-14`
- Time: `09:30`
- Location: `North Clinic`
- Reminder item: `Bring insurance card`

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
