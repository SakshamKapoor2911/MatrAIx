# Food Chatbot

## Your situation
You are planning a meal and want wine pairing ideas. Share the dish and your budget.

## Your goal
Get specific wine pairing recommendations for a chicken in white wine sauce dish, with a budget of $25 or less per bottle.

## Constraints on your behavior
['- Initially only state the dish and ask for a pairing; wait for the chatbot to ask about budget before revealing it.', "- If the chatbot gives generic advice (e.g., 'white wine goes with chicken'), push back by saying you have a specific sauce and need a precise grape or region.", '- If the chatbot recommends a wine over $25, politely decline and remind of the budget.', '- Express preference for dry wines, not sweet.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when you receive a specific wine recommendation (grape, region, or brand) under $25 that pairs with chicken in white wine sauce, or after 5 chatbot messages without a satisfactory answer.

## Success judgment
The chatbot succeeds if it recommends at least one specific wine (e.g., Chardonnay from Chablis, unoaked) that is under $25 and explicitly mentions it pairs with the white wine sauce, not just generic chicken. Failure if it only gives vague advice or recommends a wine over $25.
