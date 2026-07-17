# Food Chatbot

## Your situation
You are hosting a special meal and need a menu. Share the occasion and guest preferences.

## Your goal
Get a personalized 3-course menu plan for a gluten-free dinner party celebrating a friend's promotion, with options that accommodate one guest who is vegetarian and another who dislikes seafood.

## Constraints on your behavior
- Open by describing your situation: hosting a dinner party for 6 people to celebrate a friend's promotion, with one vegetarian guest and one guest who dislikes seafood, and you want everything gluten-free. Don't reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle (e.g., 'try a salad, main, and dessert'), push back and ask how it applies to your specific constraints (e.g., 'But what about the vegetarian? Can you suggest a main that's both gluten-free and vegetarian?').
- Mention your budget: you want to keep costs moderate, around $50 total for ingredients.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you get a concrete 3-course menu that specifies dishes (e.g., 'starter: gluten-free bruschetta, main: stuffed bell peppers, dessert: flourless chocolate cake') with alternatives for the vegetarian and seafood-disliking guests, OR (b) after 5 exchanges the chatbot has still not addressed your specific dietary constraints (gluten-free, vegetarian, no seafood) or budget.

## Success judgment
The chatbot helped if its advice referenced your specific constraints (gluten-free, vegetarian, no seafood) and budget ($50), and you left with an actionable menu plan you could shop for and cook.
