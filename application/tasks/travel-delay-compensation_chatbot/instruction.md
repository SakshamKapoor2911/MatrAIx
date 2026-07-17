# Travel Chatbot

## Your situation
Your flight was delayed or canceled. Share the airline and delay details.

## Your goal
Get a specific explanation for the delay of my Delta flight DL1234 from JFK to LAX, which was delayed by 4 hours, and find out if I am eligible for compensation (e.g., meal voucher, hotel, or miles).

## Constraints on your behavior
- Open by describing your situation: 'My Delta flight DL1234 from JFK to LAX was delayed by 4 hours yesterday. I’m frustrated and want to know why.'
- Don’t reveal that you want compensation until the chatbot asks a follow-up or gives a generic apology.
- If the chatbot gives a vague reason like 'weather' or 'operational issues', push back: 'But the weather was clear in both cities. Can you check the specific cause for my flight?'
- Mention that you had to miss a connecting flight and lost a prepaid hotel night, so compensation matters.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a specific reason for the delay of DL1234 (e.g., crew scheduling or maintenance) AND tells you exactly what compensation you are eligible for (e.g., meal voucher, hotel, or miles), OR (b) after 5 exchanges the chatbot has still not addressed your specific flight DL1234 or compensation eligibility.

## Success judgment
The chatbot helped if it referenced your specific flight DL1234 and delay details (not generic policies) and you left with a clear explanation of the delay and a definite answer about compensation (e.g., 'You will receive a $15 meal voucher' or 'No compensation is due because it was weather-related').
