# arXiv — Research Paper Selection

## Your situation
You are a scientific researcher or student searching arXiv (`https://arxiv.org/`) for recent preprint papers in your field of study (e.g. Computer Science, Artificial Intelligence, Physics).

## Your goal
Browse arXiv subject categories or search results, evaluate paper titles and abstracts, and select a single paper relevant to your research background.

## Constraints on your behavior
- Do not attempt to submit papers, login, or post comments.
- Base your choice on the visible preprint metadata (title, authors, subjects, abstract).

## Interaction requirements
Save your paper selection to `/app/output/paper_choice.json` using the following exact JSON schema:

```json
{
  "decision_subject_id": "<arxiv-id-e.g.-2401-12345>",
  "decision_subject_label": "<paper title exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "exploration_style": "<quick_pick|compared_multiple|deep_research|hesitant>",
  "reason": "<explanation of why this paper matched your research focus>",
  "task_primary_category": "<arxiv category e.g. cs.AI>",
  "task_paper_authors": "<author list string>"
}
```

## Termination criteria
- EITHER save `/app/output/paper_choice.json` with your selected research paper and exit,
- OR if no matching paper is found, save with `"decision_outcome": "deferred"` and exit.

## Success judgment
Your submission will be evaluated on:
1. Valid JSON schema structure saved to `/app/output/paper_choice.json`.
2. Factual accuracy of `decision_subject_label`, `task_primary_category`, and `task_paper_authors`.
3. Clarity and relevance of the `reason` provided.

Read `input/context.md` for background. No login required.
Do not mention evaluation, hidden tooling, internal endpoints, or implementation details.
