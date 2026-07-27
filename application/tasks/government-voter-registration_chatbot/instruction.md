# Government Chatbot

## Your situation
You recently moved to a new state and need to update your voter registration before the upcoming election in November. You're unsure about the deadline and required documents.

## Your goal
You want to successfully update your voter registration for the upcoming November election in your new state. You need to know the registration deadline and what documents are required to prove your residency and identity.

## Constraints on your behavior
- Start by asking a general question like 'How do I update my voter registration?' without specifying your new state initially.
- If the chatbot asks for your state, provide it (e.g., 'I just moved to Ohio').
- Politely push back if the chatbot gives generic advice that doesn't match your specific situation (e.g., 'That doesn't apply to me because I just moved').
- If the chatbot mentions a deadline, ask for confirmation or clarification (e.g., 'Is that the deadline to register or to update?').
- Mention that you have a driver's license from your old state but not sure if that works.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when you have received a clear answer about the exact registration deadline for your new state and the list of acceptable documents (e.g., 'So I need to provide my new address and a utility bill?'). If after 5 exchanges you still lack clarity, end with a frustrated statement.

## Success judgment
The chatbot is considered successful if it provides the specific voter registration deadline for the state (e.g., 'Ohio's deadline is 30 days before the election, which is October 5, 2024') and lists the required documents (e.g., 'You can use your new state driver's license or a utility bill with your current address'). If it only gives a link to a general website without specifics, it fails.
