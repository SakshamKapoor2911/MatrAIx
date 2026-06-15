# Notification preferences (desktop)

You just set up a new laptop. Before you finish, review how **notifications** work on this machine.

1. Open **System Settings** (or **System Preferences**) → **Notifications**.
2. Pick **one app** you actually use (for example Mail, Messages, or Safari) and review its notification style.
3. Decide whether you would **keep notifications enabled** for that app on your everyday machine.

Write your decision to `/tmp/matraix-notification-preferences/decision.json`:

```json
{
  "keep_notifications_on": true,
  "app_reviewed": "<app name you looked at>",
  "reason": "<string explaining your choice as yourself>"
}
```

`keep_notifications_on` must be `true` or `false`. Do not change unrelated system settings.
