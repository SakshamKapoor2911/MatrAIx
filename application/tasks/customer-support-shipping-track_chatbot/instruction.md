# Customer-Support Chatbot

## Your situation
You are waiting for a delivery. Share your tracking number or order details.

## Your goal
Find out the expected delivery date and current location of my package.

## Constraints on your behavior
- Start by providing the order number but not the tracking number initially.
- If asked, provide the tracking number only after the first generic response.
- Push back if the agent gives vague or generic updates without specifics.
- Mention that I need the package by Friday for a birthday.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when I get a specific delivery date and current location, or after 5 exchanges if not resolved.

## Success judgment
The chatbot successfully provided the expected delivery date and current location of the package. If it only gave generic status or failed to use the tracking number, it is unsuccessful.
