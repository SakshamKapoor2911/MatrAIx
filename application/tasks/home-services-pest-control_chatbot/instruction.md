# Home-Services Chatbot

## Your situation
You have a pest problem. Describe what you are seeing and where.

## Your goal
Get a specific identification of the pests and a targeted treatment plan, including whether I need an exterminator or can handle it myself, and a timeline for action.

## Constraints on your behavior
- Open by describing your concrete situation: 'I keep seeing small, dark brown beetles in my kitchen pantry, especially near the flour and cereal boxes. They're about 1/8 inch long and seem to come out at night.'
- Don't reveal your specific question until the chatbot asks a follow-up or gives generic advice. If it immediately suggests calling an exterminator, push back by asking if it could be pantry moths or weevils and mention you've tried cleaning and sealing containers.
- If the chatbot gives a generic listicle (e.g., 'seal cracks, remove food sources'), push back and ask how it applies to your specific named items (flour, cereal) and whether you need to throw away all open packages.
- Mention budget constraints: you prefer a DIY solution under $50 if possible, but are open to professional help if necessary.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you get a clear identification of the pest (e.g., 'those are likely sawtoothed grain beetles') and a step-by-step treatment plan that includes whether to discard specific items like flour and cereal, OR (b) after 5 exchanges the chatbot has still not addressed your specific items (flour and cereal) or constraints (budget under $50).

## Success judgment
The chatbot helped if its advice referenced your specific items (flour, cereal, beetles in pantry) and you left with an actionable first step you could take, such as 'inspect and discard all open grain products, then vacuum and wipe shelves with vinegar, and set out pheromone traps.'
