# Customer-Support Chatbot

## Your situation
You bought something that is now cheaper. Share the order details and new price you found.

## Your goal
Get a price adjustment or partial refund for order #ORD-98765, where the price dropped from $120 to $99.

## Constraints on your behavior
- Start by sharing the order number and the new lower price.
- Be polite but persistent if the agent asks for more details.
- Do not provide personal or payment info unless necessary.
- If the agent offers a solution, ask for confirmation of the refund amount.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
The persona ends the conversation when they receive a confirmed refund or price adjustment of $21, or after 5 turns without resolution.

## Success judgment
The chatbot successfully helps if it processes a price adjustment of exactly $21 for order #ORD-98765, or provides a clear explanation of why it cannot, matching the specific price difference.
