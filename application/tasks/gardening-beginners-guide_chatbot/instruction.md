# Gardening Chatbot

## Your situation
You have a 10x10 foot sunny backyard patch that's currently just dirt and weeds, and you want to grow tomatoes and basil.

## Your goal
Get a step-by-step plan for prepping the 10x10 patch, starting from clearing weeds to planting tomatoes and basil, including soil amendments and a timeline.

## Constraints on your behavior
- Open by describing your 10x10 sunny patch overrun with weeds, but do not mention wanting tomatoes and basil until the chatbot asks a follow-up or gives generic advice.
- If the chatbot suggests generic tips (e.g., 'clear weeds, add compost'), push back and ask how to handle specific weeds like crabgrass and dandelions in that small space.
- Mention your budget is under $50 for supplies, and you're not willing to buy expensive tools like a tiller.
- Ask for a specific starting date based on your local last frost date (assume mid-May) and a supply list with costs.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot gives a concrete plan including how to clear crabgrass and dandelions, soil amendment details, and a planting schedule for tomatoes and basil, OR (b) after 5 exchanges the chatbot has still not addressed your specific weeds or budget constraint.

## Success judgment
The chatbot helped if its advice referenced your specific 10x10 patch, crabgrass/dandelions, and under-$50 budget, and you left with a clear first step (e.g., 'pull dandelions by hand, smother crabgrass with cardboard, then add compost').
