# Wikipedia — Topic Article Search

## Your situation
You are using Wikipedia (`https://en.wikipedia.org/`) to locate a comprehensive, reliable reference article on a specific topic of interest. Your goal is to find an article that directly answers your inquiry and satisfies your learning style.

## Your goal
Search Wikipedia for your target topic, evaluate the main article returned, and document the key reference finding.

## Constraints on your behavior
- Do not attempt to edit pages, create user accounts, or post talk page comments.
- Only browse public Wikipedia articles without logging in.
- Base your choice on the visible article content (title, lead section, table of contents, categories).

## Interaction requirements
Save your final finding to `/app/output/article_find.json` using the following exact JSON schema:

```json
{
  "decision_subject_id": "<slugified-article-title>",
  "decision_subject_label": "<article title exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "reason": "<explanation of why this article matched your topic search>",
  "task_search_query": "<the search query used>",
  "task_article_url": "<full Wikipedia article URL>"
}
```

## Termination criteria
- EITHER save `/app/output/article_find.json` with your chosen article finding and exit,
- OR if no relevant article is found after trying multiple search queries, save the output with `"decision_outcome": "deferred"` and exit.

## Success judgment
Your submission will be evaluated on:
1. Valid JSON schema structure saved to `/app/output/article_find.json`.
2. Factual accuracy of `decision_subject_label`, `task_search_query`, and `task_article_url` matching Wikipedia.
3. Clarity and relevance of the `reason` provided.

Read `input/context.md` for background. No login required.
Do not mention evaluation, hidden tooling, internal endpoints, or implementation details.
