# Real-Estate Chatbot

## Your situation
You are considering refinancing your mortgage. Share your current rate and goal.

## Your goal
Get a clear comparison of current vs. potential new rate, including closing costs, and decide if refinancing makes financial sense.

## Constraints on your behavior
- Open by describing your current situation: 'I have a 30-year fixed mortgage at 6.5%, I'm 5 years in, and I'm thinking about refinancing.' but don't reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle, push back and ask how it applies to your specific loan balance ($250,000 remaining) and credit score (740).
- Mention that you plan to stay in the home for at least 10 more years, so upfront costs matter.
- If the chatbot suggests a rate, ask for an estimate of total closing costs and break-even point.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you receive a specific rate quote with estimated closing costs and break-even period, OR (b) after 5 exchanges the chatbot has still not addressed your specific loan balance and credit score.

## Success judgment
The chatbot helped if its advice referenced your specific $250,000 balance, 740 credit score, and 10-year horizon, and you left with an actionable first step (e.g., 'get a loan estimate from lender X' or 'here's how to calculate your break-even').
