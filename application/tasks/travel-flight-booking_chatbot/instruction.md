# Travel Chatbot

## Your situation
You need to book a flight. Share your origin destination and travel dates.

## Your goal
Book a round-trip flight from New York (JFK) to London (LHR) departing June 10, 2025 and returning June 17, 2025, with a preference for a direct flight under $800.

## Constraints on your behavior
- Open by describing your trip: 'I need to book a flight from New York to London for mid-June, returning a week later.'
- Don't reveal your specific dates or budget until the chatbot asks a follow-up or gives generic advice.
- If the chatbot suggests flights over $800 or with layovers, push back and say you specifically want direct flights under $800.
- Mention that you're flexible on exact departure time but need to arrive by evening on June 10.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a specific flight option that matches your dates, route, and budget, OR (b) after 5 exchanges the chatbot has still not addressed your specific budget constraint of under $800.

## Success judgment
The chatbot helped if it offered at least one concrete flight option with dates (June 10-17), route (JFK-LHR nonstop), and price under $800, and you could confirm the booking details.
