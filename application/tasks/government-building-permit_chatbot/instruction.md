# Government Chatbot

## Your situation
You are planning a construction project and want to know about permits. Share the project type.

## Your goal
Obtain a complete list of all required permits for a specific construction project (e.g., building a single-family home addition of 200 sq ft) and understand the application process.

## Constraints on your behavior
- Start by asking a general question about permits without specifying project details.
- After the chatbot responds, reveal that the project is a residential addition (e.g., 200 sq ft home addition) to test if the chatbot asks for specifics.
- If the chatbot provides generic advice, ask for clarification on local municipality requirements.
- Mention a tight timeline (e.g., need permits within 2 weeks) to see if the chatbot offers expedited options.

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End the conversation when the chatbot provides a detailed list of required permits for the project type and explains the application steps, or after 5 chatbot responses if still unclear.

## Success judgment
The chatbot correctly identifies the project type (e.g., residential addition) and provides a permit list including building permit, electrical permit, and plumbing permit, along with steps to apply. It should also address the timeline concern.
