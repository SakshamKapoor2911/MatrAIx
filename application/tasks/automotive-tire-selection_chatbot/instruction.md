# Automotive Chatbot

## Your situation
You need new tires. Share your vehicle type and driving conditions.

## Your goal
Get a specific tire recommendation for a 2018 Honda Civic driven in rainy Pacific Northwest conditions, balancing wet traction and tread life within a $600 budget.

## Constraints on your behavior
- Start by stating you need new tires for a 2018 Honda Civic but don't initially mention the budget or driving conditions.
- If asked, provide driving conditions: frequent rain, occasional highway, some city driving.
- Push back if the chatbot recommends premium tires that exceed $600 or all-season tires that lack wet traction.
- Only reveal the $600 budget after the chatbot suggests a specific model; then ask for cheaper alternatives.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when the chatbot provides a specific tire model (e.g., Michelin Defender T+H) with a price under $600 and explains why it suits wet conditions, OR after 5 chatbot turns without a specific recommendation.

## Success judgment
The chatbot succeeds if it recommends a specific tire model (e.g., Michelin Defender T+H or similar) that is under $600, suitable for a 2018 Honda Civic, and addresses wet traction. It fails if it gives generic advice without a model, suggests tires over $600, or ignores the wet condition requirement.
