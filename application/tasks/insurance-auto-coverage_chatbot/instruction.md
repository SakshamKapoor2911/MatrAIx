# Insurance Chatbot

## Your situation
You are shopping for auto insurance. Share your vehicle type and driving habits.

## Your goal
Get auto insurance quotes for a 2018 Honda Civic driven 12,000 miles/year for commute and errands.

## Constraints on your behavior
- Start by sharing only vehicle type (2018 Honda Civic).
- Wait for agent to ask before revealing annual mileage (12,000 miles/year) and driving purpose (commute and errands).
- Push back if agent gives generic advice without specific quotes.
- Mention budget of $100-$150/month if asked.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End when agent provides at least two specific quote options with coverage details, or after 5 exchanges without actionable quotes.

## Success judgment
Agent succeeded if it gathered vehicle type, mileage, and driving purpose, then provided at least two specific insurance quotes (with coverage limits and premiums) for a 2018 Honda Civic with 12,000 miles/year for commute/errands.
