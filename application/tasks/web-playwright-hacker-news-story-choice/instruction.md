# Hacker News — Front Page Story Selection

## Your situation
You are scanning Hacker News (`https://news.ycombinator.com/`) for interesting tech news, programming discussions, or startup posts that align with your personal tech interests and values.

## Your goal
Browse the top stories on Hacker News, evaluate title topics and submission sources, and pick a single story that most interests you.

## Constraints on your behavior
- Do not attempt to submit stories, vote, or post comments (no login required).
- Only browse the public front page and item detail pages.

## Interaction requirements
Save your story selection to `/app/output/story_choice.json` using the following exact JSON schema:

```json
{
  "decision_subject_id": "<story-id-or-slug>",
  "decision_subject_label": "<story title exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "reason": "<explanation of why this story caught your interest>",
  "task_points": "<points string e.g. 142 points>",
  "task_comment_count": "<comments count e.g. 58 comments>"
}
```

## Termination criteria
- EITHER save `/app/output/story_choice.json` with your selected story and exit,
- OR if no relevant story is found, save with `"decision_outcome": "deferred"` and exit.

## Success judgment
Your submission will be evaluated on:
1. Valid JSON schema structure saved to `/app/output/story_choice.json`.
2. Factual accuracy of `decision_subject_label`, `task_points`, and `task_comment_count` from the live site.
3. Clarity and relevance of the `reason` provided.

Read `input/context.md` for background. No login required.
Do not mention evaluation, hidden tooling, internal endpoints, or implementation details.
