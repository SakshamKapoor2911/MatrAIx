# Bookshop browsing (CUA + live web)

Browse the public book catalog at:

**https://books.toscrape.com/**

Use the **desktop browser** on this machine (visual computer-use: navigate, click, scroll). Explore the site as yourself and pick one book you would genuinely consider buying.

Write your choice to `/app/output/book_interest.json`:

```json
{
  "title": "<book title exactly as shown on the site>",
  "price_gbp": "<price string as shown, e.g. £51.77>",
  "interested": true,
  "reason": "<string explaining your choice as yourself>"
}
```

`interested` must be `true` or `false`. Base your answer only on what you see in the browser — do not invent titles or prices.

No login or purchase is required.

**Suggested agent:** `persona-computer-1` with `-e use-computer`. See `docs/applications/web-interaction.md`.
