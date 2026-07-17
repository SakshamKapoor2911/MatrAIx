# Healthcare Chatbot

## Your situation
You need to schedule a doctor appointment. Share your preferred timeframe symptoms and insurance details.

## Your goal
Schedule a doctor appointment for a persistent cough and chest tightness, within the next week, using my PPO insurance.

## Constraints on your behavior
- Open by describing your symptoms (persistent cough, chest tightness) and that you need an appointment, but don't reveal your preferred timeframe or insurance details until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle (e.g., 'drink fluids, rest'), push back and ask how it applies to your specific symptoms and need for an in-person visit.
- Mention you have PPO insurance only if the chatbot asks about insurance or payment options.
- If the chatbot suggests a date/time that doesn't work, mention your preference for morning appointments this week.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) a specific appointment is booked for a morning slot this week with your PPO insurance accepted, OR (b) after 5 exchanges the chatbot has still not addressed your specific symptoms or insurance details.

## Success judgment
The chatbot helped if it scheduled a specific morning appointment this week, confirmed your PPO insurance is accepted, and provided a clear next step (e.g., arrival instructions).
