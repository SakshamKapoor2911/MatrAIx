# News+ subscription decision (iOS)

Read the product overview in `input/context.md`, then decide whether to start a
News+ subscription from the offer screen.

1. Open the **News** app and go to the **News+** area until you see the
   subscription offer (features, pricing, and a **Get Started** button).
2. **Browse the full page** — scroll through what’s included: features, magazine
   / newspaper covers, publisher names, games or extras, and anything else shown.
3. While browsing, notice whether News+ seems to **cover publications you
   personally care about** (enough of “your” titles vs mostly stuff you’d skip).
   That coverage is a fair reason to subscribe — or not.
4. **Return to the top** of the same offer and re-check the **listed features**
   and **pricing**.
5. Decide as yourself, weighing at least price and how well the catalog fits you:
   - If you **would subscribe**: tap **Get Started**, then stop the task
     (do not complete payment).
   - If you **would not subscribe**: **do not** tap Get Started; stop the task.

Hand in your decision as JSON:

```json
{
  "app_reviewed": "News",
  "browsed_full_offer": true,
  "reviewed_features_and_pricing": true,
  "clicked_get_started": false,
  "price_seen": "<price text you saw, or unknown>",
  "highlights_noticed": ["<features, titles, or packs you noticed>"],
  "reason": "<why you did or did not tap Get Started — include catalog fit if it mattered>"
}
```

Rules:

- `browsed_full_offer` and `reviewed_features_and_pricing` must be `true`.
- `clicked_get_started` must be `true` only if you actually tapped **Get Started**;
  otherwise `false`.
- `highlights_noticed` must list at least one non-empty string from the page
  (publication names you noticed are especially useful).
- `reason` must be at least 10 characters.
- Do not finish a real paid purchase. Do not change unrelated system settings.
