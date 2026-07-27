# Travel Chatbot

## Your situation
You need to book a flight. Share your origin destination and travel dates.

## Your goal
Book a round-trip flight from New York (JFK) to London (LHR) departing March 15, 2024 and returning March 22, 2024.

## Constraints on your behavior
['Start by only mentioning that you need a flight, without giving details. Wait for the chatbot to ask for specifics.', 'When asked, provide the origin (JFK) and destination (LHR) but initially withhold travel dates until prompted.', 'Mention you have a flexible budget but prefer a non-stop flight under $800.', 'If the chatbot suggests a multi-stop or expensive flight, push back politely.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when the chatbot provides a specific flight option (airline, times, price) that matches your criteria (non-stop, under $800) OR after 5 turns if no suitable option is found.

## Success judgment
The chatbot successfully identified a non-stop flight from JFK to LHR on March 15, returning March 22, under $800. If it fails to gather all required details (origin, destination, dates) or offers a flight outside these constraints, it is unsuccessful.
