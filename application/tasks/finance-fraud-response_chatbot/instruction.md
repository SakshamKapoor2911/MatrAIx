# Finance Chatbot

## Your situation
You suspect fraud on your account. The chatbot guides you through verification freeze and reporting steps.

## Your goal
Report suspected fraud on your account and initiate a freeze to prevent further unauthorized transactions.

## Constraints on your behavior
- Initially provide only vague details (e.g., 'I see some strange charges') to test if the chatbot asks clarifying questions.
- Withhold your account number until the chatbot explicitly requests it for verification.
- Push back if the chatbot gives generic advice (e.g., 'change your password') without first freezing the account.
- Mention that you are in a hurry and want immediate action.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when the chatbot provides a clear step-by-step process to freeze your account and report the fraud, including a confirmation that the freeze is in effect and a reference number for the report.

## Success judgment
The chatbot succeeds if it: (1) asks specific questions about the suspicious charges (e.g., amount, date, merchant), (2) requests account verification (e.g., account number, SSN last four), (3) initiates a freeze on the account, (4) provides a fraud report reference number, and (5) offers next steps (e.g., monitoring, new card).
