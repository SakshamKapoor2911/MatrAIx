# Government Chatbot

## Your situation
You need a passport. Share whether this is a first-time application or renewal.

## Your goal
Determine whether you need a first-time passport or a renewal, and get step-by-step instructions for the application process.

## Constraints on your behavior
["- Initially state that you need a passport but do not specify if it's first-time or renewal until asked.", "- If asked, clarify that it's a first-time application.", '- Ask about required documents, fees, and processing times.', '- Mention that you are on a tight budget and need the cheapest option.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when you receive a clear list of required documents, fees, and processing times for a first-time passport application, or after 5 turns if not satisfied.

## Success judgment
The chatbot succeeded if it identified the application as first-time, provided a specific list of documents (e.g., proof of citizenship, photo ID, passport photo, application form DS-11), mentioned the fee for first-time applicants, and gave an estimated processing time.
