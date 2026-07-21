# Choose an MIT OpenCourseWare course

## Your situation

You are a self-directed learner choosing one university-level course to study
next. Read the scenario brief in `input/context.md`, then use the live MIT
OpenCourseWare website to make the choice.

## Your goal

Search or browse the public catalog, open and inspect at least **three distinct
course detail pages**, compare the courses, and choose the one you most want to
study next.

## Constraints on your behavior

- Use only information visible on the live MIT OCW site. Do not invent course
  metadata, prerequisites, or time commitments.
- When course resource formats matter to your decision, treat your preference
  for reading versus watching course material separately from your preferred
  format for receiving answers.
- Do not log in, enroll, download, donate, purchase, share, contact anyone, or
  visit a third-party site.

## Interaction requirements

Use the live website in the browser. Compare course descriptions, levels,
topics, and available learning-resource types when they are relevant to you.
Save your choice to `/app/output/course_choice.json`:

```json
{
  "decision_subject_id": "<course slug from the selected MIT OCW URL>",
  "decision_subject_label": "<course title copied from the main heading of its canonical course detail page>",
  "decision_outcome": "selected",
  "basis_primary": "<price|quality|features|convenience|taste|trust|familiarity|novelty|fit|other>",
  "basis_secondary": "<optional second value from the same enumeration>",
  "exploration_style": "<compared_multiple|deep_research>",
  "reason": "<why this course fits your background, interests, goals, and learning preferences, grounded in the pages you inspected>",
  "task_course_url": "https://ocw.mit.edu/courses/<course-slug>/",
  "task_course_number": "<course number exactly as shown>",
  "task_course_level": "<course level exactly as shown>",
  "task_options_considered": [
    {
      "decision_subject_id": "<course slug>",
      "decision_subject_label": "<course title copied from the main heading of its canonical course detail page>",
      "task_course_url": "https://ocw.mit.edu/courses/<course-slug>/",
      "task_course_number": "<course number exactly as shown>",
      "task_course_level": "<course level exactly as shown>",
      "task_relevance_note": "<why this was a plausible candidate for you>"
    }
  ]
}
```

## Termination criteria

- `task_options_considered` must contain at least three distinct courses whose
  detail pages you actually opened.
- For every course you record, copy its title from the main heading of that
  course's canonical detail page, not from a search result, recommendation
  card, browser title, or snippet.
- The selected course must appear in `task_options_considered`, with matching
  title, slug, URL, course number, and level.
- Use the course-page URL slug as `decision_subject_id`.
- Keep titles, course numbers, and levels faithful to the live pages; do not
  invent metadata.
- `basis_secondary` is optional. If included, it must differ from
  `basis_primary`.
- Because comparison is required, use `compared_multiple` or `deep_research`
  for `exploration_style`.
- Keep `reason` specific to what matters to you and evidence from the selected
  course page.
- Finish after saving the completed JSON file.

## Success judgment

The task is successful when the saved JSON follows the required structure, the
candidate list contains at least three course pages you visited, the selected
course matches one candidate, and all recorded titles, course numbers, levels,
slugs, and URLs are faithful to the live site.
