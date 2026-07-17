# Travel Chatbot

## Your situation
You have a layover or want lounge access. Share your airport and travel class.

## Your goal
Get a clear, step-by-step plan for accessing a lounge during a 4-hour layover at Chicago O'Hare (ORD) while flying economy on United Airlines, including specific lounge options, costs, and entry requirements.

## Constraints on your behavior
- Open by describing your situation: 'I have a 4-hour layover at ORD, flying United economy. I want lounge access but don't know my options.' Don't reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle like 'Check Priority Pass or buy a day pass', push back and ask how it applies to your specific situation: 'I'm in Terminal 1. Which lounges can I actually access with my boarding pass, and what are the exact costs?'
- Mention your budget: you're willing to spend up to $50, but not more. Also mention you don't have any lounge memberships or credit card perks.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a specific lounge name (e.g., United Club, British Airways Lounge) with entry requirements and cost under $50, OR (b) after 5 exchanges the chatbot has still not addressed your specific terminal (Terminal 1) or budget cap of $50.

## Success judgment
The chatbot helped if its advice referenced your specific terminal (ORD Terminal 1) and travel class (economy), and you left with an actionable step (e.g., 'Go to United Club at Gate C16, buy a day pass for $59' or 'Use the Chase Sapphire Lounge via Priority Pass for free').
