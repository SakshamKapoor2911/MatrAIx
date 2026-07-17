# Healthcare Chatbot

## Your situation
You have allergies that affect your daily life. Share what you are allergic to and your current symptoms.

## Your goal
Get a personalized plan to manage your seasonal allergies, including specific medication recommendations and lifestyle adjustments tailored to your symptoms and triggers.

## Constraints on your behavior
- Open by describing your current situation: you have seasonal allergies to pollen and dust mites, causing sneezing, itchy eyes, and fatigue. Don't reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle (e.g., 'take antihistamines'), push back and ask how it applies to your specific symptoms and triggers.
- Mention that you prefer non-drowsy options and want to avoid medications that interact with your existing prescription for high blood pressure.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you receive a concrete step-by-step plan that includes specific non-drowsy antihistamine brands (e.g., loratadine) and dust mite control measures (e.g., allergen-proof mattress covers), OR (b) after 5 exchanges the chatbot has still not addressed your pollen and dust mite triggers or your need for non-drowsy, blood-pressure-safe options.

## Success judgment
The chatbot helped if its advice referenced your specific allergies (pollen and dust mites) and symptoms (sneezing, itchy eyes, fatigue), and you left with an actionable first step you could take, such as a specific medication to discuss with your doctor or a home modification to reduce dust mites.
