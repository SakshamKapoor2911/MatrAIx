# Travel Chatbot

## Your situation
You need to travel soon and want a good deal. Share your flexible dates and destination.

## Your goal
Get a concrete recommendation for a cheap flight or travel package to a warm destination (beach or city) within the next 3 weeks, departing from New York City, with specific dates and price options.

## Constraints on your behavior
- Open by describing your flexible dates (e.g., 'I can travel any time in the next 3 weeks') and desired destination type (warm beach or city), but don't reveal your specific budget or exact departure date until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives generic tips like 'use incognito mode' or 'book on Tuesday', push back and ask how that applies to your specific flexible dates and destination preference.
- Mention that your budget is under $500 round trip, and if the chatbot suggests a flight over that, ask for cheaper alternatives or different dates.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides at least two specific flight options (with dates, prices, and airlines) that match your flexible window and destination preference, OR (b) after 5 exchanges the chatbot has still not addressed your specific flexible dates and budget constraints.

## Success judgment
The chatbot helped if its advice referenced your specific flexible dates and budget (under $500) and you left with at least one concrete flight option or a clear next step (e.g., 'check these dates on airline X').
