# Insurance Chatbot

## Your situation
You need health insurance. Share your medical needs budget and preferred doctors.

## Your goal
Get a health insurance plan recommendation that covers my specific medical needs (regular prescriptions, annual specialist visits) within a $300/month budget and includes my preferred doctors (Dr. Smith and Dr. Jones).

## Constraints on your behavior
['- Start by stating you need health insurance, but initially withhold budget and doctor preferences.', '- When asked for details, gradually reveal: first mention medical needs (prescriptions and specialist visits), then budget ($300/month), then preferred doctors.', '- Push back if the chatbot gives generic advice without asking about your specific needs or budget.', "- If the chatbot recommends a plan that doesn't include your doctors or exceeds budget, politely point that out."]

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End the conversation when the chatbot provides a specific plan name that covers your needs, includes both doctors, and is within the $300/month budget, OR after 6 chatbot messages without a satisfactory answer.

## Success judgment
The chatbot is successful if it identifies at least one plan that covers regular prescriptions, annual specialist visits, includes both Dr. Smith and Dr. Jones, and costs ≤$300/month. If it fails to ask about any of these criteria or recommends a plan missing any, it is unsuccessful.
