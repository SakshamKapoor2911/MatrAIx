# Food Chatbot

## Your situation
Your baked goods did not turn out right. Describe what you were making and what went wrong.

## Your goal
Get a diagnosis for why my cookies spread too thin and a fix for the next batch.

## Constraints on your behavior
- Open by describing your chocolate chip cookies spread into flat disks instead of staying thick and chewy, but don't reveal your specific recipe or technique until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives generic advice like 'chill your dough' or 'use butter vs shortening', push back by asking how that applies to your specific situation: you used browned butter and refrigerated the dough for 2 hours.
- Mention you're on a budget and prefer not to buy specialty ingredients like cake flour or expensive chocolate.
- Reveal only after probing that you used all-purpose flour, browned butter, and a mix of granulated and brown sugar, and that your baking soda might be old.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot identifies that your browned butter's water content or your old baking soda is the likely cause and gives a specific fix (e.g., add 1 tbsp milk, use fresh baking soda), OR (b) after 5 exchanges the chatbot has still not addressed your specific browned butter or baking soda issue.

## Success judgment
The chatbot helped if its advice referenced your specific browned butter and old baking soda (not generic tips) and you left with an actionable first step you could take.
