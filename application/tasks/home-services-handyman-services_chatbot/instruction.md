# Home-Services Chatbot

## Your situation
You need small home repairs. Share what needs fixing.

## Your goal
Get a prioritized list of which small home repairs to tackle first and a rough estimate of time and cost for each.

## Constraints on your behavior
- Open by describing your concrete situation: 'I have a leaky faucet in the kitchen, a squeaky door hinge, and a cracked tile in the bathroom.'
- Don't reveal your specific question (which to do first) until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle (e.g., 'fix leaks first'), push back and ask how it applies to your specific items (e.g., 'But the faucet leak is very slow and the tile crack is getting worse—should I still do the faucet first?').
- Mention you have a limited budget (under $100) and want to do it yourself, so cost of supplies matters.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot gives you a specific prioritized list with time/cost estimates for your leaky faucet, squeaky door hinge, and cracked tile, OR (b) after 5 exchanges the chatbot has still not addressed your specific repairs (leaky faucet, squeaky door hinge, cracked tile) or your budget constraint.

## Success judgment
The chatbot helped if its advice referenced your specific repairs (leaky faucet, squeaky door hinge, cracked tile) and your budget constraint, and you left with an actionable first step (e.g., 'fix the faucet first because it wastes water, costs $15, and takes 30 minutes').
