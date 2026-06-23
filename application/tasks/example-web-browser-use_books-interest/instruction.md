# Bookshop browsing (browser-use + live web)

Browse the public book catalog at:

https://books.toscrape.com/

Use the **browser-use** agent loop (Chromium + DOM/vision tools) to explore the catalog as yourself and pick one book you would genuinely consider buying.

Write your choice to `/app/output/book_interest.json`:

```json
{
  "title": "<book title exactly as shown on the site>",
  "price_gbp": "<price string as shown, e.g. £51.77>",
  "interested": true,
  "reason": "<string explaining your choice as yourself>"
}
```

`interested` must be `true` or `false`. Read titles and prices from the live page — do not invent values.

No login or purchase is required.

**Suggested agent:** `persona-browser-use`. See `docs/applications/web-interaction.md`.
