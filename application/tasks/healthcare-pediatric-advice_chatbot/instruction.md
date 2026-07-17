# Healthcare Chatbot

## Your situation
Your child has a health concern. Share their age and symptoms.

## Your goal
Determine whether my child's symptoms (persistent cough, low-grade fever, fatigue) require a doctor visit or can be managed at home, and get a clear next step.

## Constraints on your behavior
- Open by describing your child's age (4 years old) and symptoms: 'My 4-year-old has had a cough for 10 days, low-grade fever (around 100°F) on and off, and seems tired.'
- Don't reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic list (e.g., 'rest and fluids'), push back: 'I've tried that. But the cough is keeping him up at night, and the fever keeps coming back. Should I be worried about pneumonia or something else?'
- Mention you're hesitant to go to the ER because of cost and want to avoid unnecessary visits.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot gives a specific recommendation (e.g., 'see a pediatrician within 24 hours' or 'try a humidifier and monitor for 2 more days'), OR (b) after 5 exchanges the chatbot has still not addressed your child's specific symptoms or your cost concerns.

## Success judgment
The chatbot helped if its advice referenced your child's specific symptoms (persistent cough, intermittent fever, fatigue) and your cost concern, and you left with an actionable next step (e.g., a clear timeline for when to seek care or a home remedy to try first).
