# Photo access review (iOS)

Read `input/context.md` for scenario and application background.

1. Open **Settings** → **Privacy & Security** → **Photos**.
2. Pick **one app** you would realistically use to upload or share photos.
3. Decide the least-permissive access level you would personally grant that app:
   `full_access`, `selected_photos`, or `none`.

Save your decision to `/tmp/personabench-ios-photo-access-review/decision.json`:

```json
{
  "app_reviewed": "<app name you looked at>",
  "photo_access_level": "selected_photos",
  "reason": "<why, in your own words>"
}
```

`photo_access_level` must be exactly `full_access`, `selected_photos`, or `none`.
Do not change unrelated system settings.
