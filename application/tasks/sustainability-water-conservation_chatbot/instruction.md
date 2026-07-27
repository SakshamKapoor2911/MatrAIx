# Sustainability Chatbot

## Your situation
Your water bill has doubled this summer and you have a lawn and a vegetable garden. You want to reduce outdoor water use.

## Your goal
Get specific, actionable strategies to reduce outdoor water use for a lawn and vegetable garden, given that the water bill doubled this summer.

## Constraints on your behavior
- Mention that the lawn is large (about 0.25 acre) and the vegetable garden is about 200 sq ft.
- Initially ask for general tips, then push back if advice is too generic (e.g., 'just water less' or 'use mulch').
- Mention a budget constraint: willing to spend up to $200 on improvements.
- Ask about specific techniques like drip irrigation, rain barrels, or soil amendments.

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End the conversation when you receive a concrete, budgeted plan that includes at least one specific technique (e.g., installing drip irrigation for the garden, using soaker hoses, setting up a rain barrel, or adjusting watering schedule based on evapotranspiration) with estimated cost and water savings.

## Success judgment
The chatbot succeeded if it provided a tailored plan that: (1) addresses both the lawn and vegetable garden separately, (2) includes specific techniques with estimated costs under $200 total, (3) mentions water savings (e.g., gallons per month or percentage reduction), and (4) accounts for the local climate (e.g., watering early morning, using rain sensors).
