# Travel Chatbot

## Your situation
You need a rental car. Share your destination dates and vehicle preferences.

## Your goal
Book a rental car for a specific destination and dates, with a preferred vehicle type.

## Constraints on your behavior
['- Withhold the destination until the chatbot asks for it.', "- Initially state a vague preference like 'a midsize car' but later specify 'need a SUV for mountainous terrain'.", '- Mention a budget constraint of $300 total for the rental period.', '- Push back if the chatbot suggests a car without confirming dates first.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when the chatbot provides a specific rental car option that matches the destination (Denver), dates (June 10-15), vehicle type (SUV), and total cost under $300.

## Success judgment
The chatbot successfully identifies the destination (Denver), dates (June 10-15), and vehicle preference (SUV), and offers a rental car option within the $300 budget.
