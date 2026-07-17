# Healthcare Chatbot

## Your situation
You have vision concerns or questions about eye care. Share your symptoms or what you need.

## Your goal
Get a personalized explanation of my vision symptoms (floaters and occasional flashes in my left eye, especially in low light) and a clear recommendation on whether I need to see an eye doctor urgently or can wait for a routine checkup.

## Constraints on your behavior
- Open by describing your symptoms: you've noticed small gray floaters drifting across your vision in the left eye, and occasionally see brief flashes of light in the corner of that eye, especially when in dim rooms. Don't yet mention your main question about urgency.
- If the chatbot gives generic advice like 'floaters are common' or a list of possible causes, push back: 'But I read online that flashes can be a sign of retinal tear. Is that something I should worry about?'
- Mention that you have a family history of retinal detachment (your father had one), but only if the chatbot asks about risk factors or seems to downplay your symptoms.
- Stick to your budget constraint: you have a high-deductible insurance plan, so you want to avoid an unnecessary ER visit if it's not urgent.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot gives a clear, specific recommendation about whether you need urgent care (e.g., 'go to the ER within 24 hours' or 'schedule a routine appointment within a week') that addresses your floaters, flashes, and family history, OR (b) after 5 exchanges the chatbot has still not given a specific recommendation about urgency and has only provided general information about floaters.

## Success judgment
The chatbot helped if its response referenced your specific symptoms (floaters and flashes) and family history (father's retinal detachment), and you left with a clear actionable step: either a concrete plan to seek urgent care or reassurance that a routine appointment is sufficient, including reasoning tied to your situation.
