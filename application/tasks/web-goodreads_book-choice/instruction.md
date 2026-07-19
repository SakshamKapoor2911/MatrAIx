# Goodreads — Book Choice & Recommendation

## Your situation
You are a reader looking for a book recommendation on Goodreads (`https://www.goodreads.com/`) that matches your reading taste, favorite genres, and community ratings.

## Your goal
Browse popular books or choice awards on Goodreads, evaluate ratings and genres, and select a single book for your reading list.

## Constraints on your behavior
- Do not attempt to log in, sign up, or write reviews.
- Base your choice on public book listings, ratings, and genre tags.

## Interaction requirements
Save your book choice to `/app/output/book_choice.json` using the following exact JSON schema:

```json
{
  "decision_subject_id": "<slugified-book-title-or-isbn>",
  "decision_subject_label": "<book title exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "reason": "<explanation of why this book was chosen>",
  "task_author": "<book author name>",
  "task_rating": "<average rating e.g. 4.15>"
}
```

## Termination criteria
- EITHER save `/app/output/book_choice.json` with your selected book and exit,
- OR if no matching book is found, save with `"decision_outcome": "deferred"` and exit.

## Success judgment
Your submission will be evaluated on:
1. Valid JSON schema structure saved to `/app/output/book_choice.json`.
2. Factual accuracy of `decision_subject_label`, `task_author`, and `task_rating`.
3. Clarity and relevance of the `reason` provided.

Read `input/context.md` for background. No login required.
Do not mention evaluation, hidden tooling, internal endpoints, or implementation details.
