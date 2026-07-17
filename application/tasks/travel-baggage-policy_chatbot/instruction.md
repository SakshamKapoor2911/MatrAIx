# Travel Chatbot

## Your situation
You need to know baggage rules for your flight. Share your airline and fare type.

## Your goal
Find out the exact baggage allowance (carry-on and checked) for my specific fare type and understand any fees or size/weight restrictions.

## Constraints on your behavior
- Open by describing your situation: 'I'm flying with Spirit Airlines on a Basic Economy fare next week, and I'm confused about what bags are included.'
- Don't reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic answer about standard policies, push back: 'But I heard Basic Economy has different rules. Can you confirm if a personal item is free and what size it needs to be?'
- Mention you're on a tight budget and want to avoid unexpected fees.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides the specific baggage allowance for Spirit Airlines Basic Economy, including size/weight limits and fees for carry-on and checked bags, OR (b) after 5 exchanges the chatbot has still not addressed your specific airline and fare type.

## Success judgment
The chatbot helped if its advice referenced your specific airline (Spirit Airlines) and fare type (Basic Economy), and you left knowing exactly what bags are included, their size/weight limits, and any fees for additional bags.
