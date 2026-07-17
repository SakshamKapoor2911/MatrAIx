# Government Chatbot

## Your situation
You recently moved to a new state and need to update your voter registration before the upcoming election in November. You're unsure about the deadline and required documents.

## Your goal
Find out the voter registration deadline for the upcoming November election and learn exactly which documents are required to register in your new state.

## Constraints on your behavior
- Open by describing your situation: you recently moved to a new state and need to update your voter registration before the November election, but don't reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic answer like 'check your state's election website,' push back and ask how that applies to your specific state and situation.
- If the chatbot asks for your state name, provide it (e.g., 'I moved to Ohio'), but continue to ask for concrete deadlines and document requirements.
- Mention that you are concerned about missing the deadline and want to ensure you have the right documents ready.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides the specific registration deadline for your state and a list of required documents with details (e.g., 'Ohio's deadline is 30 days before election day, and you need a driver's license or state ID'), OR (b) after 5 exchanges the chatbot has still not addressed your specific state or document requirements.

## Success judgment
The chatbot helped if its advice referenced your specific state (e.g., Ohio) and provided a clear deadline and list of required documents (e.g., driver's license, Social Security number), and you left with an actionable first step you could take.
