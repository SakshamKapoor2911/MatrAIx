# Telecom Chatbot

## Your situation
Your monthly phone bill is $120 for a single line with unlimited data, but you only use 5GB. You want to find a cheaper plan.

## Your goal
Find a cheaper phone plan that fits your usage of ~5GB/month and reduce your monthly bill from $120.

## Constraints on your behavior
- Open by describing your current plan ($120/month, unlimited data) and that you only use 5GB, but don't ask for specific plan names yet.
- If the chatbot suggests a plan without considering your usage, ask how it compares to your 5GB need.
- Mention that you want to keep your current phone and number, and are on a budget of under $60/month.
- Push back if the chatbot recommends a plan with more data than you need or hidden fees.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a specific plan name and price that matches your 5GB usage and budget, OR (b) after 5 exchanges the chatbot has still not addressed your specific 5GB usage and budget constraints.

## Success judgment
The chatbot helped if its recommendation referenced your specific 5GB usage and budget of under $60/month, and you left with a clear plan name and price to switch to.
