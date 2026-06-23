# Notification preferences (iOS)

You just set up a new iPhone. Before you finish, take a minute to see how **notifications** work on this phone.

1. Open **Settings** → **Notifications**.
2. Pick **one app** you actually use (Mail, Messages, Safari, whatever) and look at how its notifications are set up.
3. Decide whether you'd **keep notifications on** for that app on a phone you use every day.

Hand in your decision as JSON:

```json
{
  "keep_notifications_on": true,
  "app_reviewed": "<app name you looked at>",
  "reason": "<why, in your own words>"
}
```

`keep_notifications_on` must be `true` or `false`. Don't change unrelated system settings.
