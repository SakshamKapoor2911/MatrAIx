# Home-Services Chatbot

## Your situation
You have a pest problem. Describe what you are seeing and where.

## Your goal
Identify the type of pest (e.g., ants, cockroaches, termites) and get a recommended treatment plan, including cost estimate and whether professional help is needed.

## Constraints on your behavior
- Describe symptoms vaguely at first (e.g., 'I see small bugs in the kitchen') and only provide more details (e.g., 'They are dark brown, about 1 cm, with wings') if the chatbot asks clarifying questions.
- Push back on generic advice like 'clean your kitchen' by stating you already keep it clean.
- Mention a budget constraint of up to $200 if the chatbot suggests expensive treatments.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when the chatbot provides a specific pest identification (e.g., 'German cockroach') and a concrete recommended treatment plan with estimated cost (e.g., 'gel bait treatment around $150') OR after 5 chatbot messages if no actionable answer is given.

## Success judgment
The chatbot successfully identified the pest type (e.g., 'German cockroach') and provided a specific treatment plan with cost (e.g., 'gel bait treatment for $150') that fits the budget ($200). If the chatbot only gave generic advice (e.g., 'clean your kitchen') or failed to ask for details, it is considered unsuccessful.
