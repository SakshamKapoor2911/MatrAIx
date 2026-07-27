# Travel Chatbot

## Your situation
You are considering a cruise. Share your preferred region duration and budget.

## Your goal
Find a 7-night cruise in the Caribbean for under $1500 per person, including port fees and taxes.

## Constraints on your behavior
['- Initially mention only that you want a cruise, but not the budget or duration.', "- When asked, reveal you prefer the Caribbean but don't specify a duration yet.", '- Push back if the agent suggests longer or more expensive cruises.', '- After the agent asks about budget, state your budget of $1500 per person and duration of 7 nights.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation once the agent provides at least one specific cruise option (name, date, and price) that meets the criteria of 7 nights, Caribbean, and under $1500 per person including port fees and taxes.

## Success judgment
The chatbot is successful if it recommends a specific cruise that matches the location (Caribbean), duration (7 nights), and budget ($1500 per person including fees). If the chatbot only gives generic advice or fails to confirm the price includes port fees and taxes, it fails.
