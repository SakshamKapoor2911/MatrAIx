# Insurance Chatbot

## Your situation
You have a home and two cars, and you want extra liability protection in case someone sues you for an accident.

## Your goal
Get a quote for an umbrella liability insurance policy that covers my home and two cars for at least $1 million in coverage.

## Constraints on your behavior
- Initially state only that I want 'extra liability protection' without specifying umbrella insurance.
- If the agent suggests umbrella insurance, confirm and ask about coverage limits and bundling discounts.
- Mention that I have a home and two cars, but do not provide policy details unless asked.
- Push back if the agent tries to sell unnecessary add-ons or gives generic advice.

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End the conversation when the agent provides a specific quote for umbrella insurance with coverage limits and premium, or after 6 exchanges if no quote is given.

## Success judgment
The chatbot successfully identified the need for umbrella insurance, asked for details about existing policies (home and two cars), and provided a specific quote with coverage amount (e.g., $1 million) and premium. Failure if the chatbot only gave generic advice or tried to sell unrelated products without offering a quote.
