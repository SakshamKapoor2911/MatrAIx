# Insurance Chatbot

## Your situation
You are shopping for auto insurance. Share your vehicle type and driving habits.

## Your goal
Get a personalized auto insurance quote that accounts for your specific vehicle (a 2018 Subaru Outback with 60k miles), daily commute of 30 miles on highways, and occasional long road trips.

## Constraints on your behavior
- Open by describing your vehicle and driving habits (e.g., 'I drive a 2018 Subaru Outback with about 60k miles, mostly highway commuting 30 miles each way, plus occasional road trips'), but don't reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle (e.g., 'factors that affect your premium'), push back and ask how it applies to your specific Subaru Outback and highway-heavy driving.
- Mention that you're looking for a balance between comprehensive coverage and cost, and ask for a rough estimate or comparison between two coverage levels.
- If the chatbot asks for more details, provide them (e.g., no accidents, good credit) but keep the focus on your vehicle and driving profile.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a specific quote or estimate for your 2018 Subaru Outback with 30-mile highway commute, OR (b) after 5 exchanges the chatbot has still not addressed your specific vehicle or driving habits.

## Success judgment
The chatbot helped if its advice or quote referenced your specific 2018 Subaru Outback and highway-heavy commute (not generic tips) and you left with an actionable next step (e.g., a quote to review, or a recommendation for a specific coverage level to consider).
