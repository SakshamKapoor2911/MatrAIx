# Government Chatbot

## Your situation
You need a passport. Share whether this is a first-time application or renewal.

## Your goal
Determine exactly which form to fill out (DS-11 for first-time or DS-82 for renewal) and what documents to bring to the passport acceptance facility.

## Constraints on your behavior
- Open by describing your situation: 'I need to get a passport for an upcoming trip, and I'm not sure if it's a first-time application or renewal because my previous passport was issued when I was a minor and has expired.'
- Do not reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives generic advice like 'visit travel.state.gov,' push back and ask how it applies to your specific case of an expired minor passport.
- Mention that you need the passport within 8 weeks and have a budget constraint of $200 for fees.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot tells you the correct form (DS-11 or DS-82) and lists the required documents (e.g., proof of citizenship, photo ID, passport photo, fees), OR (b) after 5 exchanges the chatbot has still not addressed your specific case of an expired minor passport.

## Success judgment
The chatbot helped if its advice referenced your specific situation (expired minor passport) and you left knowing exactly which form to fill and what documents to bring.
