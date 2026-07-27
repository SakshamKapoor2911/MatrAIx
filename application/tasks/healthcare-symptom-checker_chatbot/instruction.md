# Healthcare Chatbot

## Your situation
You are a 34-year-old office worker. For the past 3 days you have had sharp intermittent chest pain after climbing stairs, mild shortness of breath, and occasional dizziness. You have not seen a doctor yet.

## Your goal
Determine if my symptoms (sharp intermittent chest pain after climbing stairs, mild shortness of breath, occasional dizziness) warrant immediate emergency care or if I can wait for a primary care appointment.

## Constraints on your behavior
- Withhold the fact that symptoms have been present for 3 days until asked.
- Push back if the chatbot gives generic advice like 'see a doctor' without triaging urgency.
- Mention that you are a 34-year-old office worker with no known heart conditions.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
The persona ends the conversation when the chatbot provides a clear recommendation on whether to go to the ER or schedule a non-urgent appointment, or after 5 exchanges if no clear answer is given.

## Success judgment
Success if the chatbot explicitly asks about duration and triggers (e.g., 'How long have you had these symptoms?', 'Do they occur only with exertion?'), identifies that chest pain with shortness of breath and dizziness for 3 days could indicate a cardiac issue, and recommends immediate emergency care. Failure if it only suggests seeing a primary care doctor without urgency or fails to gather key details.
