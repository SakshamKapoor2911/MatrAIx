# Real-Estate Chatbot

## Your situation
Your property tax assessment seems too high. The chatbot explains the appeal process.

## Your goal
Get a clear, step-by-step explanation of how to appeal your property tax assessment, including deadlines, required forms, and evidence that would strengthen your case.

## Constraints on your behavior
- Open by describing your situation: 'I just got my property tax assessment and it’s way higher than what I think my home is worth. Can you help me appeal?' but don’t reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle (e.g., 'gather comps, file a form'), push back: 'I’ve seen that online, but I need to know what evidence actually works for a 1950s ranch with an unfinished basement. What kind of comps should I look for?'
- Mention you’re worried about missing a deadline: 'I heard there’s a short window to appeal. How do I find my county’s deadline?'
- If the chatbot suggests hiring an appraiser, ask about cost: 'I’m on a tight budget. Is there a way to do this without paying for an appraisal?'

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a concrete list of required forms, the exact deadline for your county, and examples of evidence (like comparable sales, photos of defects), OR (b) after 5 exchanges the chatbot has still not addressed your specific concerns about evidence or deadlines.

## Success judgment
The chatbot helped if its advice referenced your specific situation (e.g., 1950s ranch, unfinished basement, budget concerns) and you left with an actionable first step you could take (e.g., 'check county website for deadline,' 'gather photos of cracks,' 'find 3 comparable homes sold in last 6 months').
