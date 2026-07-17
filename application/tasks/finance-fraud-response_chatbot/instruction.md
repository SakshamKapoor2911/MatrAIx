# Finance Chatbot

## Your situation
You suspect fraud on your account. The chatbot guides you through verification freeze and reporting steps.

## Your goal
Get step-by-step guidance to freeze your account and report the suspected fraud, including confirmation that the freeze is in effect and a case/reference number for the report.

## Constraints on your behavior
- Open by describing that you noticed several unauthorized transactions on your account, but don't reveal the specific amounts or dates until the chatbot asks for details.
- If the chatbot gives generic advice like 'contact your bank,' push back and ask for specific steps to freeze the account and report fraud.
- Mention that you're worried about your savings account being drained and ask if freezing one account affects others.
- State that you need a case number or confirmation for your records.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you have frozen your account and received a case number for the fraud report, OR (b) after 5 exchanges the chatbot has still not provided specific freeze instructions or a case number.

## Success judgment
The chatbot helped if it provided specific steps to freeze your account (e.g., 'log into online banking, go to settings, click freeze') and issued a case number or confirmation that the freeze was placed.
