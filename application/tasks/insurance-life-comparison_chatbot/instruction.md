# Insurance Chatbot

## Your situation
You are considering life insurance. Share your age dependents and financial obligations.

## Your goal
Determine whether term life or whole life insurance is better for your situation, and get a specific quote or estimate for coverage amount and monthly premium.

## Constraints on your behavior
- Open by describing your situation: 'I'm 42, have two kids aged 8 and 10, and a mortgage of $250,000. I want to make sure they're covered if something happens.'
- Do not reveal your specific question about term vs whole life until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives generic advice like 'life insurance is important', push back and ask how that applies to your specific dependents and mortgage.
- Mention that you have a monthly budget of $100-150 for insurance.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you receive a specific recommendation (term or whole life) with a rough premium estimate for a $250,000 policy, OR (b) after 5 exchanges the chatbot has still not addressed your specific dependents and mortgage.

## Success judgment
The chatbot helped if its advice referenced your specific age (42), kids (8 and 10), mortgage ($250,000), and budget ($100-150), and you left with a clear recommendation (term vs whole life) and a next step (e.g., get a quote, talk to an agent).
