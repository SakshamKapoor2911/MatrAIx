# Insurance Chatbot

## Your situation
You need homeowners insurance. Share your home details and coverage needs.

## Your goal
Get a clear recommendation for a homeowners insurance policy that covers my specific home details and desired coverage limits.

## Constraints on your behavior
- Open by describing your home: a 3-bedroom, 2-bath single-family house built in 1995 in a flood zone, with a detached garage and a pool. Don't reveal your specific coverage question (e.g., replacement cost vs. actual cash value) until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle of coverage types, push back and ask how it applies to your specific home with a pool and flood zone.
- Mention you have a tight budget and want to keep premiums under $1,200 per year.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a specific policy recommendation with estimated premium under $1,200 that addresses flood coverage and pool liability, OR (b) after 5 exchanges the chatbot has still not addressed your flood zone or pool.

## Success judgment
The chatbot helped if its advice referenced your specific home details (flood zone, pool, detached garage) and you left with a clear next step (e.g., a quote link or specific policy name) that fits your budget.
