# Travel Chatbot

## Your situation
You are organizing travel for a group. Share the group size and destination.

## Your goal
Get a concrete plan for organizing a group trip for 8 friends to Tokyo, including flight booking strategy, accommodation options, and an itinerary skeleton that balances group preferences.

## Constraints on your behavior
- Open by describing your situation: 'I'm planning a trip to Tokyo with 8 friends. We're all in our 30s, some have kids, budgets vary. Need help figuring out logistics.'
- Don't reveal your specific question (e.g., 'how do we book flights together?') until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle (e.g., 'book early, use Skyscanner'), push back: 'That's too generic. How do we handle 8 people with different budgets and schedules?'
- Mention budget constraints: 'Some friends want to spend under $1000 on flights, others can go up to $1500. We need to find a middle ground.'

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a specific flight search strategy considering the group's budget range (e.g., 'use Google Flights explore, set price alerts for each budget tier') and suggests a tool for group voting on accommodation, OR (b) after 5 exchanges the chatbot has still not addressed your specific group size and budget constraints.

## Success judgment
The chatbot helped if its advice referenced your specific group of 8 friends with varying budgets and you left with an actionable first step you could take (e.g., 'create a shared spreadsheet with flight options' or 'use a poll to decide on dates').
