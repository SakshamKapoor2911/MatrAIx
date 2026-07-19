# MDN Web Docs — API & Web Technology Search

## Your situation
You are a developer researching web standards, API specifications, and JavaScript/CSS references on MDN Web Docs (`https://developer.mozilla.org/`). You need to locate official documentation for a web technology concept or API feature.

## Your goal
Search MDN Web Docs for the specified technology topic, navigate to the relevant reference page, and record the documentation details.

## Constraints on your behavior
- Do not attempt to log in or edit MDN articles.
- Base your choice strictly on the official documentation pages (page title, description, code examples, browser compatibility).

## Interaction requirements
Save your final finding to `/app/output/doc_find.json` using the following exact JSON schema:

```json
{
  "decision_subject_id": "<slugified-doc-title>",
  "decision_subject_label": "<doc title exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "reason": "<explanation of why this documentation page satisfied your query>",
  "task_search_query": "<search term used>",
  "task_doc_url": "<full MDN document URL>"
}
```

## Termination criteria
- EITHER save `/app/output/doc_find.json` with your chosen reference document and exit,
- OR if no relevant documentation is found, save the output with `"decision_outcome": "deferred"` and exit.

## Success judgment
Your submission will be evaluated on:
1. Valid JSON schema structure saved to `/app/output/doc_find.json`.
2. Factual accuracy of `decision_subject_label`, `task_search_query`, and `task_doc_url` matching MDN.
3. Logical alignment of the `reason` provided.

Read `input/context.md` for background. No login required.
Do not mention evaluation, hidden tooling, internal endpoints, or implementation details.
