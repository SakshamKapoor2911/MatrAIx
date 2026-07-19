# Books to Scrape — Book Selection

## Your situation
You are browsing Books to Scrape (`https://books.toscrape.com/`) looking for a book that aligns with your reading preferences, current budget, and purpose for buying. You care about picking a title that fits your genre interest while remaining within your spending limit.

## Your goal
Browse the book catalog, evaluate available titles, and select a single book that best matches your persona criteria.

## Constraints on your behavior
- Do not make any real purchases or submit personal financial details.
- Only browse public product pages and categories without logging in.
- Base your choice strictly on the visible book information (title, price, availability, rating, genre category).

## Interaction requirements
Save your final selection to `/app/output/book_choice.json` using the following exact JSON schema:

```json
{
  "decision_subject_id": "<slugified-book-title-or-upc>",
  "decision_subject_label": "<book title exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "reason": "<explanation of why this book was selected for your persona>",
  "task_book_price": "<price string e.g. £51.77>",
  "task_book_genre": "<genre category name>"
}
```

## Termination criteria
- EITHER save `/app/output/book_choice.json` with your chosen book selection and exit,
- OR if no matching book is found after browsing multiple categories, save the output with `"decision_outcome": "deferred"` and exit.

## Success judgment
Your submission will be evaluated on:
1. Valid JSON schema structure saved to `/app/output/book_choice.json`.
2. Factual accuracy of `decision_subject_label`, `task_book_price`, and `task_book_genre` matching the real catalog.
3. Logical alignment between your persona preferences and the `reason` provided.

Read `input/context.md` for background. No login required.
Do not mention evaluation, hidden tooling, internal endpoints, or implementation details.
