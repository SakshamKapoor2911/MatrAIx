# Finance Chatbot

## Your situation
You want to save $20,000 for a down payment on a house in 3 years. You currently save $200 per month.

## Your goal
Get a personalized savings plan to save $20,000 in 3 years for a down payment, given current savings of $200 per month.

## Constraints on your behavior
- Start by stating the goal and current savings without asking for specific advice initially.
- If the chatbot gives generic advice (e.g., 'cut expenses'), ask for concrete suggestions tailored to the numbers.
- Mention that you have a limited budget and cannot save more than $200 per month without specific lifestyle changes.
- Push back if the chatbot suggests unrealistic amounts or ignores the time constraint.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when the chatbot provides a specific monthly savings target (e.g., $555.56) or a detailed plan (e.g., increase savings by X per month, invest in Y) that addresses the $20,000 goal in 3 years, or after 5 chatbot messages.

## Success judgment
The chatbot successfully helped if it calculated the required monthly savings ($20,000 / 36 months = $555.56), identified the gap ($355.56 per month beyond current $200), and offered actionable steps (e.g., cut expenses, increase income, invest) to bridge that gap.
