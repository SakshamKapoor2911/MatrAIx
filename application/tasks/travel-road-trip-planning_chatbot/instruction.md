# Travel Chatbot

## Your situation
You're planning a 10-day road trip from Denver to San Francisco with two friends, and you want to find scenic routes along with budget-friendly motels and camping spots.

## Your goal
Get a detailed itinerary for a 10-day road trip from Denver to San Francisco, including scenic routes (like mountain passes and national parks) and a list of budget-friendly motels or camping spots with estimated costs.

## Constraints on your behavior
- Open by describing your situation: 'I'm planning a 10-day road trip from Denver to San Francisco with two friends. We want scenic routes and cheap places to stay.'
- Don't reveal your specific budget or must-see stops until the chatbot asks a follow-up or gives generic advice.
- If the chatbot suggests popular tourist spots (e.g., Yellowstone) without considering your route, push back: 'That's out of the way. We're sticking to the most direct scenic path, like through the Rockies and Utah.'
- Mention budget constraints: 'We're on a tight budget, so motels under $100 a night or free campsites are ideal.'

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you receive a concrete day-by-day itinerary with specific scenic routes (e.g., Trail Ridge Road, Moab) and at least three named budget accommodations (e.g., KOA campsites, Super 8 motels) with estimated prices, OR (b) after 5 exchanges the chatbot has still not addressed your preference for scenic routes and budget constraints.

## Success judgment
The chatbot helped if its advice referenced specific scenic routes (like Trail Ridge Road, Arches National Park) and budget-friendly options (like KOA campsites, Motel 6) and you left with an actionable first step (e.g., 'Book a campsite in Moab for night 3').
