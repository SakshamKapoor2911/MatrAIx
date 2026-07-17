# Finance Chatbot

## Your situation
You need to send money. Share where to and how much.

## Your goal
Find the best method to send $500 to your brother in Mexico, considering fees, exchange rates, and speed.

## Constraints on your behavior
- Open by describing your situation: you need to send money to your brother in Mexico, but don't specify the amount or method until the chatbot asks a follow-up or gives generic advice.
- If the chatbot suggests a generic option like PayPal or bank transfer, push back by asking about hidden fees and exchange rates for sending to Mexico.
- Mention that your brother needs the money within 2 days and you want to minimize costs.
- Set a budget: you're willing to pay up to $10 in fees but want the best exchange rate.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you get a clear recommendation with fee and exchange rate comparisons for sending $500 to Mexico within 2 days, OR (b) after 5 exchanges the chatbot has still not addressed your specific destination (Mexico) and time constraint (2 days).

## Success judgment
The chatbot helped if its advice referenced your specific destination (Mexico) and amount ($500), compared fees and exchange rates for at least two services, and you left with an actionable next step (e.g., use a specific service like Wise or Remitly).
