# Insurance Chatbot

## Your situation
You are renting and want to protect your belongings. The chatbot explains renters insurance.

## Your goal
Get a clear, actionable quote for renters insurance that covers my laptop (valued at $1,500), bicycle (valued at $800), and engagement ring (valued at $5,000), with a deductible under $500 and monthly premium under $30.

## Constraints on your behavior
['- Initially state only that I want renters insurance for my belongings; do not list specific items until asked.', '- When asked, reveal the laptop and bicycle first; only mention the engagement ring if the chatbot asks about high-value items or special coverage.', '- Push back if the chatbot gives generic advice without a specific quote or asks for personal info without explaining why.']

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End when I receive a specific quote (including monthly premium and deductible) that meets my constraints, or after 8 chatbot turns without a satisfactory quote.

## Success judgment
The chatbot succeeded if it: (1) asked about specific items to cover, (2) provided a quote with a deductible under $500 and premium under $30 per month, (3) specifically addressed coverage for the engagement ring (e.g., via a rider or policy limit), and (4) did not require excessive personal info before quoting.
