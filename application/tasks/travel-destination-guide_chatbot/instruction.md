# Travel Chatbot

## Your situation
You are planning a trip and want to know what to do there. Share your destination travel style and interests.

## Your goal
Get personalized activity recommendations for a 5-day trip to Tokyo, Japan, focusing on cultural sites, food tours, and off-the-beaten-path experiences.

## Constraints on your behavior
- Initially only mention that you're interested in 'culture and food' without specifying Tokyo.
- After the chatbot suggests a destination, confirm it's Tokyo and ask for specific recommendations.
- Push back if the chatbot gives generic advice like 'visit temples' without naming specific temples or tours.
- Mention you have a moderate budget (willing to spend up to $100 per activity) and prefer walking or public transport.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
The persona ends the conversation after receiving at least 3 specific, named recommendations (e.g., 'Senso-ji Temple', 'Tsukiji Outer Market food tour') that fit within the budget and travel style.

## Success judgment
The chatbot is successful if it provides at least 3 concrete, named activities in Tokyo (e.g., specific temples, food tours, hidden alleys) that cost under $100 each and are accessible by public transport or walking. Generic answers like 'visit temples' or 'try local food' without specifics count as failure.
