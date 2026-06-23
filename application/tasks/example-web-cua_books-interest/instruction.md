# Bookshop browsing

There's a book catalog at:

https://books.toscrape.com/

Browse it in the desktop browser and pick one title you'd actually consider buying.

When you're done, **submit your choice as JSON** with a **done** action (Harbor writes the file for you — do not use Save dialogs or manual file editing):

```json
{
  "title": "<title as shown on the site>",
  "price_gbp": "<price as shown, e.g. £51.77>",
  "interested": true,
  "reason": "<why, in your own words>"
}
```

`interested` must be `true` or `false`. Only use titles and prices you see on the page. No need to log in or buy anything.

`Ctrl+Alt+T` opens a terminal if you need it for browsing, but **finish with a done action**, not by saving files yourself.
