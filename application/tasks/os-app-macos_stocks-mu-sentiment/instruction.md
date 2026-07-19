# Stock Sentiment: Micron Technology (MU)

Use the **Stocks** app on this Mac to research MU and form your buy/sell/hold
opinion, taking into account what you see in the app and the earnings context
provided above.

1. The **Stocks** app is already open and maximized on screen.
   Search for **MU** (Micron Technology) using the search bar and select it.
2. Review the stock's **price chart** across ALL of the following time ranges
   (click each one in the chart toolbar):
   - **1W** (1 Week)
   - **1M** (1 Month)
   - **3M** (3 Months)
   - **1Y** (1 Year)
   - **2Y** (2 Years)
   For each, note whether the trend is up/down/flat and the approximate % move.
3. Scroll down to the **News** section. Scan the headlines and use your own
   judgment to decide which (if any) are relevant to your buy/sell/hold decision.
   - Read **at most 3 articles** — only those you believe will meaningfully
     inform your decision. Quality over quantity.
   - To read an article, **click the headline** — it will open in a browser
     window (Stocks links to Yahoo Finance etc.). Immediately **maximize the
     browser window** by clicking the **green full-screen button** at the
     top-left corner.
   - **Scroll through the entire article** to read the full content before
     closing.
   - When done reading, **close the browser tab** (Cmd+W) to return to the
     Stocks app, then check remaining headlines.
   - If no headlines look relevant to MU's outlook at all, you may skip this
     step entirely (and leave `news_articles_read` as an empty `[]`).
4. Taking into account the chart trends across all timeframes, the news article
   content, and the earnings context provided above, decide whether you would
   **buy**, **sell**, or **hold** MU right now.

Save `/app/output/sentiment.json`:

```json
{
  "ticker": "MU",
  "viewed_chart": true,
  "timeframes_checked": ["1W", "1M", "3M", "1Y", "2Y"],
  "trend_summary": {
    "1W": "<brief description: up/down/flat and rough % move>",
    "1M": "<brief description>",
    "3M": "<brief description>",
    "1Y": "<brief description>",
    "2Y": "<brief description>"
  },
  "news_articles_read": [
    {
      "headline": "<article headline>",
      "summary": "<2-3 sentence summary of what the article said>",
      "relevance": "<why this article matters for your decision>"
    }
  ],
  "sentiment": "<buy | sell | hold>",
  "confidence": <1-10>,
  "reasoning": "<2-4 sentences explaining your decision, referencing specific chart trends, news content, and the earnings context>"
}
```

Rules:

- `viewed_chart` must be `true`.
- `timeframes_checked` must include at least `"1W"`, `"1M"`, `"1Y"`, and one of
  `"3M"` or `"2Y"`.
- Each entry in `trend_summary` must be a non-empty string (at least 10 chars).
- `news_articles_read` may be empty `[]` if no headlines are relevant; otherwise
  it must contain **at most 3** articles, each with a non-empty `headline`, a
  `summary` (≥20 chars), and a `relevance` explanation (≥10 chars).
- `sentiment` must be exactly one of: `"buy"`, `"sell"`, or `"hold"`.
- `confidence` must be an integer from 1 to 10.
- `reasoning` must be at least 50 characters and reference specific observations
  from charts, news, and the earnings context.
- Do not execute any trades or change any settings — only observe and decide.
- **Do NOT manually search the internet** — no Google, no typing URLs, no
  browsing beyond the article pages that Stocks opens for you.
  Base your decision solely on: (a) the Stocks app content (charts + news
  articles linked from the app), and (b) the earnings context provided above.
- Do NOT use Spotlight or open any other application besides what Stocks opens.
