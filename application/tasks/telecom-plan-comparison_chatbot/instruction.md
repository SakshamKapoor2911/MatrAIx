# Telecom Chatbot

## Your situation
You are shopping for a phone plan. Share your data usage and number of lines.

## Your goal
Find a phone plan that fits my data usage (5GB/month) and covers 2 lines, with a preference for a prepaid option under $60/month total.

## Constraints on your behavior
- Open by describing your situation: 'I need a plan for 2 lines, I use about 5GB of data per month, and I'm looking for something affordable.'
- Do not reveal your budget or prepaid preference until the chatbot asks a follow-up or gives generic advice.
- If the chatbot suggests a plan over $60 or with more data than you need, push back: 'That's more than I want to spend. Can you suggest something cheaper?'
- If the chatbot gives a generic list of plans without considering your 5GB usage and 2 lines, ask: 'How does this apply to my specific needs? I only use 5GB.'

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you receive a specific plan recommendation that covers 2 lines with 5GB data or less for under $60/month total, OR (b) after 5 exchanges the chatbot has still not addressed your specific data usage of 5GB and 2 lines.

## Success judgment
The chatbot helped if its recommendation referenced your specific 5GB data usage and 2 lines (not generic tips) and you left with an actionable plan name and price that meets your budget.
