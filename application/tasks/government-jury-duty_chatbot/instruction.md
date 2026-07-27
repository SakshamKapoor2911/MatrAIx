# Government Chatbot

## Your situation
You received a jury summons. The chatbot explains what to do.

## Your goal
You want to know exactly what steps you need to take to respond to a jury summons, including whether you can defer or be excused, and the deadline for response.

## Constraints on your behavior
['- Start by stating you received a jury summons and asking what you need to do.', "- If the chatbot gives generic advice without specifics (e.g., 'follow the instructions on the form'), push back and ask for concrete steps.", '- If the chatbot asks for details, provide them one at a time (e.g., your county, the date on the summons, your reason for needing deferral).', '- Mention that you have a pre-planned vacation during the summons period and ask if you can defer.']

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total) to fully resolve your questions.

## Termination criteria
End the conversation when you have received a clear, actionable answer about how to respond, including confirmation that you can defer due to vacation and the deadline to do so, OR after 5 turns if not resolved.

## Success judgment
The chatbot is successful if it provides specific instructions for your county (e.g., a website link or phone number), explains how to request a deferral with your vacation dates, and states the response deadline (e.g., 'within 5 days of receiving the summons').
