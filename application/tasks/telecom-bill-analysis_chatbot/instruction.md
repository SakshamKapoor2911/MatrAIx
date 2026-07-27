# Telecom Chatbot

## Your situation
Your monthly phone bill is $120 for a single line with unlimited data, but you only use 5GB. You want to find a cheaper plan.

## Your goal
Find a phone plan that costs less than $120/month, with at least 5GB of data, preferably with unlimited talk and text, for a single line.

## Constraints on your behavior
['- Start by stating you have a $120 unlimited data plan but only use 5GB, and want a cheaper option.', '- Push back if the agent suggests a plan with less than 5GB of data or adds extra fees that make the total over $90.', '- Ask about any promotional discounts or loyalty offers after receiving initial options.', '- If the agent asks for account details, provide only your current plan price and usage, not personal info like SSN.']

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End the conversation when you have received a specific plan recommendation (name and price) that meets your criteria and you have asked about discounts, or after 5 turns without a satisfactory offer.

## Success judgment
The chatbot is successful if it recommends a plan that costs $90 or less per month, includes at least 5GB of data, unlimited talk and text, and mentions any applicable discounts or promotions. If it fails to meet these criteria or does not provide a concrete plan name and price, it is unsuccessful.
