# Finance Chatbot

## Your situation
You have multiple debts and want to simplify payments. Share your debt amounts and interest rates.

## Your goal
Get a concrete plan to consolidate or simplify payments for your multiple debts, including which debts to prioritize and a specific method (e.g., balance transfer, debt consolidation loan, or snowball/avalanche method) that fits your financial situation.

## Constraints on your behavior
- Open by describing your debts: a credit card with $5,000 at 22% APR, a personal loan with $10,000 at 12% APR, and a car loan with $15,000 at 6% APR. Don't reveal your specific question about consolidation until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle (e.g., "just pay off high-interest debt first"), push back and ask how it applies to your specific debt amounts and interest rates, especially the car loan which has lower interest but higher balance.
- Mention that you have a monthly budget of $500 for extra debt payments and want to minimize total interest paid.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a specific recommendation on whether to use avalanche or snowball method for your exact debts, including a calculation of total interest and timeline, OR (b) after 5 exchanges the chatbot has still not addressed your specific debt amounts and interest rates, instead giving only generic advice.

## Success judgment
The chatbot helped if its advice referenced your specific debts (credit card $5,000 at 22%, personal loan $10,000 at 12%, car loan $15,000 at 6%) and you left with an actionable first step, such as a specific strategy (e.g., avalanche: pay minimums on car and personal loan, put all extra $500 toward credit card) or a recommendation for a specific consolidation product.
