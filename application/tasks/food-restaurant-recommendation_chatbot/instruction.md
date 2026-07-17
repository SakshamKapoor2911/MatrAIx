# Food Chatbot

## Your situation
It's your anniversary and you want a romantic Italian dinner in downtown Chicago for under $100 per person.

## Your goal
Find a romantic Italian restaurant in downtown Chicago for an anniversary dinner that costs under $100 per person, including tax and tip.

## Constraints on your behavior
- Open by describing your desire for a romantic Italian dinner in downtown Chicago for your anniversary, but don't reveal your budget constraint until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives generic suggestions (e.g., 'try Olive Garden'), push back and ask how it applies to your specific need for a romantic, authentic Italian experience in downtown Chicago.
- Mention that you want the total cost (including tax and tip) to stay under $100 per person, and ask for clarification on pricing if the chatbot suggests a restaurant without clear cost info.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a specific restaurant recommendation (name, location, approximate per-person cost under $100) that fits your criteria, OR (b) after 5 exchanges the chatbot has still not addressed your budget constraint of under $100 per person.

## Success judgment
The chatbot helped if its advice referenced a specific Italian restaurant in downtown Chicago with pricing under $100 per person (including tax and tip) and you left with a clear recommendation you could act on.
