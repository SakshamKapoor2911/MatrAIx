# Real-Estate Chatbot

## Your situation
You are planning a move. Share your distance volume and budget.

## Your goal
Get an estimate of moving costs and logistics for a 500-mile move with a 1-bedroom apartment (approx. 500 cu ft) under a $2000 budget.

## Constraints on your behavior
- Start by stating you are moving 500 miles with a 1-bedroom apartment. Do not mention budget initially.
- If the chatbot asks about budget, then disclose $2000 max.
- Push back if the chatbot suggests full-service moving (too expensive) or gives generic advice.
- Ask about DIY vs. hybrid options and hidden fees.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when you receive a specific cost estimate and recommendation for a DIY or hybrid option that fits the $2000 budget and 500 cu ft volume, or after 5 chatbot messages without a satisfactory answer.

## Success judgment
The chatbot successfully provided a concrete moving cost estimate (e.g., truck rental + fuel ~$X, or PODS quote ~$Y) that is ≤ $2000 for 500 cu ft over 500 miles, and included actionable next steps (e.g., booking a truck, ordering pods). If the chatbot only gives vague advice or fails to address budget and volume, it fails.
