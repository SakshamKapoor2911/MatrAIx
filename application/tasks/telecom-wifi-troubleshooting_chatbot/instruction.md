# Telecom Chatbot

## Your situation
Your WiFi is not working well. Describe the issue and what you have tried.

## Your goal
Get a clear diagnosis of why my WiFi is intermittently dropping, and a step-by-step plan to fix it without waiting for a technician visit.

## Constraints on your behavior
- Open by describing your WiFi issue: it works fine for 10-15 minutes, then drops for 2-3 minutes before reconnecting. You've already restarted the router twice.
- Don't reveal your specific question until the chatbot asks a follow-up or gives generic advice. If they suggest restarting again, mention you already tried that.
- If the chatbot gives generic tips like 'move the router to a central location', push back by saying your router is already centrally located and asking what else could cause intermittent drops.
- Mention you're on a budget and prefer not to buy new equipment unless absolutely necessary.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot suggests a specific cause (e.g., channel interference, outdated firmware) and gives a concrete step to test or fix it, OR (b) after 5 exchanges the chatbot has still not addressed your intermittent dropping issue and keeps giving generic advice.

## Success judgment
The chatbot helped if its advice referenced your specific symptom (intermittent drops after 10-15 minutes) and you left with an actionable first step you could take, such as changing the WiFi channel, updating router firmware, or running a specific diagnostic tool.
