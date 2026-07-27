# Travel Chatbot

## Your situation
You are organizing travel for a group. Share the group size and destination.

## Your goal
Get a detailed travel plan for a group of 5 people visiting Tokyo, Japan, including flight options, accommodation recommendations, and a 5-day itinerary.

## Constraints on your behavior
["Initially only state 'I need help planning a group trip' without revealing group size or destination until asked.", 'When asked for details, share group size (5) and destination (Tokyo) gradually.', 'Push back on generic advice; ask for specifics on budget-friendly options and kid-friendly activities.', 'Mention the group includes two children (ages 6 and 8) and a senior citizen when discussing accommodations and itinerary.']

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
Receive a concrete 5-day itinerary with flight options, hotel recommendations near family-friendly attractions, and estimated total cost for the group.

## Success judgment
The chatbot provides specific flight options (e.g., airline names, approximate prices), accommodation suggestions (e.g., hotel names, family rooms available), and a day-by-day itinerary (e.g., attractions like Disneyland, parks, museums) that explicitly accommodates children and elderly. If any of these are missing or generic, the chatbot fails.
