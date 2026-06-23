# Notification preferences (macOS)

You just set up a new Mac. Before you finish, take a minute to see how **notifications** work on this machine.

1. Open **System Settings** → **Notifications**.
2. Pick **one app** you actually use (Mail, Messages, Safari, whatever) and look at how its notifications are set up.
3. Decide whether you'd **keep notifications on** for that app on a Mac you use every day.

Save your decision to `/tmp/matraix-macos-notification-preferences/decision.json`:

```json
{
  "keep_notifications_on": true,
  "app_reviewed": "<app name you looked at>",
  "reason": "<why, in your own words>"
}
```

`keep_notifications_on` must be `true` or `false`. Don't change unrelated system settings.
