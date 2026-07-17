# Insurance Chatbot

## Your situation
You live in an earthquake-prone area and want to understand coverage. Share your home type and location.

## Your goal
Understand whether your renters insurance covers earthquake damage to your apartment in San Francisco, and if not, get a clear quote for a separate earthquake policy.

## Constraints on your behavior
- Open by describing your situation: you live in a 2-bedroom apartment in San Francisco, California, and you're worried about earthquake coverage.
- Don't reveal your specific question about renters vs. earthquake policy until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle about earthquake insurance, push back and ask how it applies to your specific apartment building (built in 1920, unreinforced masonry).
- Mention your budget: you can spend up to $50/month extra on earthquake coverage.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a specific quote for earthquake insurance for your 1920s San Francisco apartment, OR (b) after 5 exchanges the chatbot has still not addressed your specific building type or given a concrete premium estimate.

## Success judgment
The chatbot helped if its advice referenced your specific apartment (built 1920, unreinforced masonry) and you left with an actionable next step (e.g., a quote, a recommendation to contact your insurer, or a clear explanation of coverage limits).
