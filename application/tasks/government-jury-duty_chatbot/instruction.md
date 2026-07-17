# Government Chatbot

## Your situation
You received a jury summons. The chatbot explains what to do.

## Your goal
Understand the exact steps I need to take to respond to my jury summons, including how to confirm or defer service, and what documents or information I need to prepare.

## Constraints on your behavior
- Open by describing your situation: 'I just got a jury summons in the mail and I'm not sure what to do first.'
- If the chatbot gives generic advice like 'respond online,' push back and ask for specifics: 'Where exactly do I respond online? Is there a website or a phone number?'
- Mention that you work out of state and need to know if you can defer: 'I work in another state during the week, so I might need to postpone. How do I request a deferral?'
- Ask about consequences if you miss a deadline: 'What happens if I don't respond in time?'

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a clear step-by-step plan covering how to respond, deferral process, and consequences of non-response, OR (b) after 5 exchanges the chatbot has still not addressed your specific concern about deferring due to out-of-state work.

## Success judgment
The chatbot helped if its advice included specific instructions for responding (e.g., website URL, phone number), explained how to request a deferral for out-of-state work, and mentioned what happens if you miss the deadline.
