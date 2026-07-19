# Letterboxd — Film Discovery & Selection

## Your situation
You are a film enthusiast browsing Letterboxd (`https://letterboxd.com/`) to find a movie to watch. You care about picking a film that aligns with your movie taste and mood.

## Your goal
Browse trending or popular films on Letterboxd, evaluate film details and ratings, and select a single movie to add to your watchlist.

## Constraints on your behavior
- Do not attempt to create an account, log in, or write reviews.
- Base your choice on visible public film cards and movie pages.

## Interaction requirements
Save your film selection to `/app/output/movie_choice.json` using the following exact JSON schema:

```json
{
  "decision_subject_id": "<slugified-film-title-or-year>",
  "decision_subject_label": "<film title exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "reason": "<explanation of why this film appealed to your movie taste>",
  "task_release_year": "<release year e.g. 2023>",
  "task_average_rating": "<average rating e.g. 4.2>"
}
```

## Termination criteria
- EITHER save `/app/output/movie_choice.json` with your chosen movie and exit,
- OR if no appealing film is found, save with `"decision_outcome": "deferred"` and exit.

## Success judgment
Your submission will be evaluated on:
1. Valid JSON schema structure saved to `/app/output/movie_choice.json`.
2. Factual accuracy of `decision_subject_label`, `task_release_year`, and `task_average_rating`.
3. Clarity and relevance of the `reason` provided.

Read `input/context.md` for background. No login required.
Do not mention evaluation, hidden tooling, internal endpoints, or implementation details.
