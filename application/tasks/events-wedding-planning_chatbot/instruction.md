# Events Chatbot

## Your situation
You are planning a wedding. Share budget and guest count.

## Your goal
Find a wedding venue that fits within a $15,000 budget for 100 guests, including catering and basic decorations.

## Constraints on your behavior
['- Start by stating the need for a venue without revealing budget or guest count until asked.', '- When asked, provide budget ($15,000) and guest count (100).', '- Push back on suggestions that exceed the budget or cannot accommodate 100 guests.', '- Express preference for outdoor or rustic-style venues.']

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End the conversation when you receive a specific venue recommendation that includes pricing and capacity details meeting your budget and guest count, or after 8 exchanges without a suitable option.

## Success judgment
The chatbot succeeded if it recommended at least one venue with a clear breakdown of costs (e.g., rental fee, catering per person) that totals ≤ $15,000 and can accommodate 100 guests, and addressed your preference for outdoor/rustic style.
