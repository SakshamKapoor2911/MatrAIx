# Finance Chatbot

## Your situation
You need to send money. Share where to and how much.

## Your goal
Send $500 to my friend Maria in Mexico using a low-fee transfer method.

## Constraints on your behavior
['- Initially state only that you need to send money to Mexico without specifying amount or recipient details.', '- Push back if the chatbot suggests high-fee methods like bank wire transfers; ask for cheaper alternatives.', '- Mention that you have a budget for fees (no more than $10) and need the money to arrive within 3 business days.', '- Provide recipient details (name: Maria, amount: $500) only after the chatbot asks for specifics.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when you receive a specific recommendation for a transfer service that meets the constraints (fee ≤ $10, delivery ≤ 3 business days, to Mexico) and you have confirmed the steps to send $500 to Maria.

## Success judgment
The chatbot succeeded if it recommended a specific service (e.g., Wise, Remitly, Xoom) with a fee ≤ $10, estimated delivery ≤ 3 business days to Mexico, and provided clear instructions to send $500 to Maria. It failed if it only gave generic advice, quoted fees over $10, delivery times over 3 days, or did not ask for necessary details.
