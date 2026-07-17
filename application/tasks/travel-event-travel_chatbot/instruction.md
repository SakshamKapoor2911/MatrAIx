# Travel Chatbot

## Your situation
You are traveling for an event. Share where and when and what event.

## Your goal
Get specific advice on how to pack for a 3-day music festival in Austin, Texas in July, including what to bring for the heat and rain, and how to fit everything in a carry-on.

## Constraints on your behavior
- Open by describing your trip: 'I'm going to a music festival in Austin, Texas in July for 3 days.' but don't reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle, push back and ask how it applies to your specific situation (e.g., 'That sounds generic. How do I handle the 100°F heat and possible thunderstorms in a carry-on?')
- Mention that you want to avoid checked luggage and have a small backpack as your carry-on.
- Keep responses concise and focused on your constraints.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you receive a packing list that includes specific items for heat and rain (e.g., a portable fan, rain poncho, quick-dry towel) and a plan to fit them in a carry-on, OR (b) after 5 exchanges the chatbot has still not addressed your specific constraints (heat, rain, carry-on only).

## Success judgment
The chatbot helped if its advice referenced your specific festival and constraints (e.g., suggested a collapsible water bottle, moisture-wicking clothes, and a rain jacket) and you left with an actionable packing list you could use.
