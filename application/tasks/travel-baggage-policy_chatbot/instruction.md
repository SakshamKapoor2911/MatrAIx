# Travel Chatbot

## Your situation
You need to know baggage rules for your flight. Share your airline and fare type.

## Your goal
Get the baggage allowance and fees for my flight on Spirit Airlines with a Basic Economy fare.

## Constraints on your behavior
['- Start by asking about baggage rules without specifying airline or fare type immediately.', '- If the chatbot asks for more details, provide airline (Spirit Airlines) and fare type (Basic Economy).', '- Push back if the chatbot gives generic advice not specific to Spirit Basic Economy.', '- Do not mention any baggage dimensions or weight limits unless the chatbot asks.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when the chatbot provides the exact baggage allowance (carry-on and checked) and any associated fees for Spirit Basic Economy, or after 5 chatbot turns without a satisfactory answer.

## Success judgment
The chatbot must specify that Spirit Basic Economy allows only one personal item (free) and charges for carry-on and checked bags, with exact fee amounts (e.g., $35-$45 for carry-on at booking, $30-$40 for checked). If the chatbot fails to mention Spirit-specific rules or gives general advice, it is not successful.
