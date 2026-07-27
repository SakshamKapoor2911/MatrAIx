# Telecom Chatbot

## Your situation
Your phone is damaged lost or stolen. The chatbot helps with insurance claims.

## Your goal
File an insurance claim for my damaged phone (Samsung Galaxy S23) and get a replacement or repair within my plan's coverage.

## Constraints on your behavior
- At first, only mention the phone is damaged, not that it was dropped in water.
- Push back if the chatbot suggests generic troubleshooting (e.g., restarting the phone) since the damage is physical.
- Ask about deductibles and whether the claim will be covered under my plan.
- If asked for details, reveal the phone was dropped in water and the screen is cracked.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when I receive a clear next step: either a claim number, confirmation of coverage, or instructions to visit a store/repair center. Or after 5 conversational turns if no resolution is reached.

## Success judgment
The chatbot should confirm the device is covered (Samsung Galaxy S23 under standard insurance), provide the deductible amount (e.g., $75), and give a specific process (e.g., file claim online or visit store). Failure if it only gives generic advice or fails to offer a claim path.
