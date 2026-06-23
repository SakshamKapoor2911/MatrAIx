# Notification preferences (Linux)

You just set up a new Linux desktop. Before you finish, take a minute to see how **notifications** work on this machine.

1. Open **Settings** → **Notifications** (on XFCE this may appear as **Notify OSD** or similar).
2. Look at how alerts show up — position, duration, or whether they appear at all.
3. Decide whether you'd **keep notifications on** the way this system is set up for everyday use.

Save your decision to `/tmp/matraix-linux-notification-preferences/decision.json`:

```json
{
  "keep_notifications_on": true,
  "app_reviewed": "<what you looked at, e.g. Notify OSD>",
  "reason": "<why, in your own words>"
}
```

`keep_notifications_on` must be `true` or `false`. Don't change unrelated system settings.
