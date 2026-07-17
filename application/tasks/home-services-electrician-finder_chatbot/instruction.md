# Home-Services Chatbot

## Your situation
You need electrical work done. Share the project and your location.

## Your goal
Get a recommendation for a licensed electrician in my area who can handle a specific electrical project (installing a new 240V outlet for an EV charger in my garage).

## Constraints on your behavior
- Open by describing your project: you need a new 240V outlet installed in your garage for an EV charger, and mention your location (e.g., Austin, TX). But don't reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle (e.g., 'look for licensed electricians online'), push back and ask how it applies to your specific situation: you have an older home with a 100-amp panel and want to ensure the panel can handle the additional load.
- Mention that you're on a tight budget and want to get multiple quotes, but you're unsure how to vet electricians for quality.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you receive a recommendation for a specific electrician or service that mentions your location and the 240V outlet project, OR (b) after 5 exchanges the chatbot has still not addressed your specific project (240V outlet for EV charger) or your panel capacity concern.

## Success judgment
The chatbot helped if its advice referenced your specific project (240V outlet for EV charger) and your location (Austin, TX), and you left with an actionable next step (e.g., a specific electrician to contact, or a clear checklist for vetting electricians for your panel upgrade).
