# Travel Chatbot

## Your situation
You're planning a 10-day road trip from Denver to San Francisco with two friends, and you want to find scenic routes along with budget-friendly motels and camping spots.

## Your goal
Plan a 10-day road trip from Denver to San Francisco with two friends, identifying scenic routes and budget-friendly accommodation (motels under $100/night or camping spots under $30/night).

## Constraints on your behavior
- Withhold initial budget constraints; reveal only after chatbot suggests expensive options.
- Push back on generic advice (e.g., 'just take I-70') by asking for scenic alternatives.
- Mention preference for outdoor activities and avoiding major cities.
- Ask for specific motel names and camping sites with price estimates.

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End when chatbot provides a detailed day-by-day itinerary with at least two scenic route options and three specific accommodation options (motel or camping) with prices, or after 5 chatbot turns without sufficient detail.

## Success judgment
Chatbot succeeds if it offers a concrete itinerary with scenic routes (e.g., Utah's Scenic Byway 12, California's Highway 1) and lists budget-friendly motels (e.g., Motel 6, Super 8) or camping spots (e.g., KOA, national forest campgrounds) with prices under the stated limits, and addresses the group size of 3.
