# Shortcuts Gallery picks (macOS)

Browse the Shortcuts Gallery on this Mac and choose **three shortcuts** you
would most want to add. Use the background context provided above to guide your
thinking.

1. Open the **Shortcuts** app — use Spotlight (Cmd+Space), type "Shortcuts",
   and press Enter to launch it directly.
2. Go to the **Gallery** (click "Gallery" in the sidebar or toolbar).
3. Browse through the available categories — scroll through the full page so you
   see what's on offer (e.g. Essentials, Starter Shortcuts, Quick Shortcuts,
   and any other sections Apple shows).
4. For each category you see, briefly consider whether the shortcuts in it match
   your daily routine, work, hobbies, or personal needs.
5. **Pick three shortcuts** you would most want to add to your own library.
   They can come from the same category or different ones — choose whichever
   three would be genuinely most useful to you.

Save `/app/output/picks.json`:

```json
{
  "browsed_gallery": true,
  "categories_seen": ["<category names you scrolled through>"],
  "picks": [
    {
      "name": "<exact shortcut name as shown in Gallery>",
      "category": "<the Gallery category it appeared in>",
      "reason": "<why you want this shortcut — connect it to your needs>"
    },
    {
      "name": "<shortcut 2>",
      "category": "<category>",
      "reason": "<reason>"
    },
    {
      "name": "<shortcut 3>",
      "category": "<category>",
      "reason": "<reason>"
    }
  ]
}
```

Rules:

- `browsed_gallery` must be `true`.
- `categories_seen` must list at least two category names you actually saw.
- `picks` must contain exactly three items.
- Each pick's `name` must be a non-empty string matching a shortcut you saw.
- Each pick's `reason` must be at least 10 characters and explain personal fit.
- Do not actually add or run any shortcut — only browse and decide.
- Do not change unrelated system settings.
