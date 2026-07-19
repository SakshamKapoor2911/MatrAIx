# Choose an MIT OpenCourseWare course

Read the scenario brief in `input/context.md`. Use the live MIT OpenCourseWare
website to choose the **one course you would most want to study next**.

Search or browse the catalog, then open and inspect at least **three distinct
course pages** before deciding. Compare the course descriptions, level, topics,
and available learning-resource types when they are relevant to you.
When course resource formats matter to your decision, treat your preference for
reading versus watching course material separately from your preferred format
for receiving answers.

Save your choice to `/app/output/course_choice.json`:

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

Requirements:

- `task_options_considered` must contain at least three distinct courses whose
  detail pages you actually opened.
- The selected course must appear in `task_options_considered`, with matching
  title, slug, URL, course number, and level.
- Use the course-page URL slug as `decision_subject_id`.
- Keep titles, course numbers, and levels faithful to the live pages; do not
  invent metadata.
- `basis_secondary` is optional. If included, it must differ from
  `basis_primary`.
- Because comparison is required, use `compared_multiple` or `deep_research`
  for `exploration_style`.
- Keep `reason` specific to both your persona and evidence from the selected
  course page.

No login, enrollment, download, donation, purchase, sharing, contact action, or
third-party-site visit is required.
