# Legal Chatbot

## Your situation
You were injured in an accident. Share what happened.

## Your goal
Get a clear, step-by-step plan for documenting your injuries and evidence from the accident, including what to say to insurance adjusters and what documents to gather before calling a lawyer.

## Constraints on your behavior
- Open by describing your accident: you were hit by a delivery van while cycling, broke your wrist and have ongoing back pain, but don't reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives generic advice like 'seek medical attention' or 'contact a lawyer', push back and ask how it applies to your specific situation—e.g., you already saw a doctor but the back pain is lingering, and you're worried about how to handle the delivery company's insurance adjuster who keeps calling.
- Mention that you're hesitant to talk to a lawyer too early because you're worried about costs, and you want to know what you can do on your own first.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot gives you a concrete list of 3-5 documents to gather (e.g., medical records, photos of the scene, witness contact info, bike repair estimate, and a log of your pain symptoms) and explains how to respond to the adjuster's calls, OR (b) after 5 exchanges the chatbot has still not addressed your specific concerns about the adjuster and the back pain evidence.

## Success judgment
The chatbot helped if its advice referenced your specific accident (delivery van, cycling, broken wrist, back pain) and you left with an actionable first step you could take, such as a template for what to say when the adjuster calls next, or a clear order of what to document first.
