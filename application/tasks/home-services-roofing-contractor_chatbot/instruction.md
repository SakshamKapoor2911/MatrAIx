# Home-Services Chatbot

## Your situation
You need roofing work. Share whether this is repair or replacement.

## Your goal
Get a clear recommendation on whether to repair or replace the roof, including a rough cost estimate and timeline for the recommended option.

## Constraints on your behavior
- Open by describing your concrete situation: 'I have a 20-year-old asphalt shingle roof with a few missing shingles and a small leak in the corner.' but don't reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle, push back and ask how it applies to your specific roof age and damage.
- Mention that you're on a tight budget and need the most cost-effective solution.
- Ask for specific details like warranty, material options, and whether partial repair is feasible.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot gives a clear recommendation (repair or replacement) with a rough cost range and timeline, OR (b) after 5 exchanges the chatbot has still not addressed your specific roof age and damage pattern.

## Success judgment
The chatbot helped if it gave a recommendation based on your roof's age (20 years) and specific damage (missing shingles, leak), and you left with an actionable next step (e.g., schedule an inspection, or a clear decision to repair vs replace).
