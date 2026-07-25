# Choose an MIT OpenCourseWare course

## Your situation
You are a self-directed learner evaluating university-level course options on MIT OpenCourseWare. You do not have a predetermined subject or fixed shortlist. You need to browse the live catalog at https://ocw.mit.edu/search/ and inspect multiple courses to select the single best course to study next based on your background, goals, difficulty preferences, and learning resource formats.

## Your goal
Search or browse the public catalog, open and inspect at least **three distinct course pages**, compare options, and save your final course selection to `/app/output/course_choice.json`.

## Constraints on your behavior
- Do not perform any login, enrollment, download, donation, purchase, sharing, contact action, or third-party site visit.
- Rely strictly on information visible on the live MIT OCW site; do not invent course metadata, prerequisites, or time commitments.
- Treat your preference for reading versus watching course material separately from your preferred format for receiving answers.

## Interaction requirements
1. Navigate the live MIT OCW site via Playwright to search or browse course offerings.
2. Inspect at least 3 distinct course detail pages.
3. Save your choice to `/app/output/course_choice.json` matching the following schema:
```json
{
  "decision_subject_id": "<course slug from the selected MIT OCW URL>",
  "decision_subject_label": "<course title exactly as shown>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "basis_secondary": "<optional second value from the same enumeration>",
  "exploration_style": "<compared_multiple|deep_research>",
  "reason": "<why this course fits you, grounded in your persona and the pages you inspected>",
  "task_course_url": "https://ocw.mit.edu/courses/<course-slug>/",
  "task_course_number": "<course number exactly as shown>",
  "task_course_level": "<course level exactly as shown>",
  "task_options_considered": [
    {
      "decision_subject_id": "<course slug>",
      "decision_subject_label": "<course title exactly as shown>",
      "task_course_url": "https://ocw.mit.edu/courses/<course-slug>/",
      "task_course_number": "<course number exactly as shown>",
      "task_course_level": "<course level exactly as shown>",
      "task_relevance_note": "<why this was a plausible candidate for you>"
    }
  ]
}
```

## Termination criteria
- Save `/app/output/course_choice.json` after comparing at least 3 distinct course pages.
- `basis_secondary` is optional; if present, it must differ from `basis_primary`.
- Set `exploration_style` to `compared_multiple` or `deep_research`.

## Success judgment
- `/app/output/course_choice.json` exists and validates against the schema.
- `task_options_considered` contains at least 3 distinct courses whose detail pages were visited.
- The selected course matches one of the entries in `task_options_considered`.
- Titles, course numbers, levels, and URLs are faithful to live site content.

