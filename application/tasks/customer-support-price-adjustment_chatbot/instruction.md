# Customer-Support Chatbot

## Your situation
You bought something that is now cheaper. Share the order details and new price you found.

## Your goal
Get a refund for the price difference on a recently purchased item that has gone on sale.

## Constraints on your behavior
- Open by describing your purchase and the new lower price, but don't explicitly ask for a refund until the chatbot responds or asks for clarification.
- If the chatbot offers a generic policy statement, push back by referencing your specific order details and the price difference.
- Mention that you are a loyal customer and expect the price adjustment as a courtesy.
- Be polite but persistent; do not accept a simple 'no' without escalation.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot confirms a refund or store credit for the price difference, OR (b) after 5 exchanges the chatbot has still not addressed your specific order number and the price difference.

## Success judgment
The chatbot helped if it referenced your specific order number and the price difference, and you left with a clear next step (e.g., refund processed, credit issued, or a concrete timeline for resolution).
