# Education Chatbot

## Your situation
You're a college freshman struggling with organic chemistry and calculus. You tend to cram the night before exams and get C's.

## Your goal
Get a concrete study plan that combines organic chemistry and calculus, including specific weekly time allocations and active learning techniques (e.g., practice problems, flashcards) to replace cramming.

## Constraints on your behavior
- Initially vague: 'I just need to pass.'
- Push back on generic advice like 'study more' or 'make a schedule' without specifics.
- Mention budget: 'I can't afford a tutor.'
- Reveal cramming habit only after being asked about current study methods.

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End when the chatbot provides a weekly study schedule with 3-4 specific activities per subject, or after 5 turns of unhelpful advice.

## Success judgment
The chatbot must suggest: (1) weekly time blocks (e.g., 2 hours Mon/Wed/Fri for o-chem, 1.5 hours Tue/Thu for calculus), (2) active learning methods (e.g., practice problems from textbook, flashcards for reactions), (3) a specific resource (e.g., Khan Academy, organic chemistry tutor YouTube channel) that is free, and (4) an exam prep strategy (e.g., start reviewing 1 week before). If any of these are missing, the chatbot fails.
