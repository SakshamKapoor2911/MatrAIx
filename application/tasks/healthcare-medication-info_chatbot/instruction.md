# Healthcare Chatbot

## Your situation
You are taking or considering a medication. Share the name and your concerns.

## Your goal
Get clear, personalized information about the side effects of metformin and whether it's safe to take with your current over-the-counter supplements (vitamin D and a multivitamin).

## Constraints on your behavior
- Open by describing your situation: 'I’ve been prescribed metformin for prediabetes, and I’m worried about side effects. I also take vitamin D and a multivitamin daily.'
- Don't reveal your specific question about supplement interactions until the chatbot asks a follow-up or gives generic advice about metformin side effects.
- If the chatbot gives a generic listicle about metformin side effects without addressing your supplements, push back: 'That’s helpful, but does metformin interact with vitamin D or multivitamins? I take both.'
- Mention that you're concerned about long-term use and if there are ways to minimize side effects.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot gives a specific answer about metformin's interaction with vitamin D and multivitamins, including any timing or dosage adjustments needed, OR (b) after 5 exchanges the chatbot has still not addressed your specific question about supplement interactions.

## Success judgment
The chatbot helped if its advice referenced your specific supplements (vitamin D and multivitamin) by name and provided actionable guidance on whether to continue them with metformin, including any timing or dosage adjustments.
