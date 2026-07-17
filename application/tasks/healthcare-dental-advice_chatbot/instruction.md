# Healthcare Chatbot

## Your situation
You have a dental concern or want advice on oral care. Share your symptoms or questions.

## Your goal
Get a clear, step-by-step plan for managing persistent tooth sensitivity to cold and sweet foods, including whether you need to see a dentist or can try home remedies first.

## Constraints on your behavior
- Open by describing your symptoms: sharp pain when eating ice cream or drinking cold water, and occasional discomfort with sugary snacks. Don't reveal your specific question about whether to see a dentist until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle (e.g., 'use sensitive toothpaste, avoid extreme temperatures'), push back by asking how these apply to your specific situation: 'But I've already tried sensitive toothpaste for a month with no improvement. What else can I do?'
- Mention that you're on a tight budget and uninsured, so you want to avoid unnecessary dental visits if possible.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot gives you a concrete action plan that includes whether to see a dentist or try a specific home remedy with reasoning, OR (b) after 5 exchanges the chatbot has still not addressed your specific toothpaste failure or budget concerns.

## Success judgment
The chatbot helped if its advice referenced your specific symptom (sharp pain with cold and sweet) and your failed attempt with sensitive toothpaste, and you left with an actionable first step you could take (e.g., 'try a toothpaste with stannous fluoride' or 'schedule a dental exam to check for enamel erosion').
