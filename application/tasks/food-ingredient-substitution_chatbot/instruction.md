# Food Chatbot

## Your situation
You are missing an ingredient or need a substitute. Share the ingredient and why you need a replacement.

## Your goal
Find a suitable substitute for buttermilk to use in a pancake recipe, ensuring the pancakes remain fluffy and slightly tangy.

## Constraints on your behavior
- Open by describing your situation: you're making pancakes and realized you're out of buttermilk, but don't mention the specific recipe or why you need it until the chatbot asks.
- If the chatbot gives generic substitutes like milk+vinegar, ask how to adjust the quantities to match the tanginess and acidity needed for fluffy pancakes.
- Mention that you have whole milk and lemon juice at home, and ask if that combination will work or if there's a better option.
- Push back if the advice is too vague; ask for specific measurements and whether the substitute will affect the texture.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a specific substitute with measurements and explains how it affects the pancakes' fluffiness and tanginess, OR (b) after 5 exchanges the chatbot has still not addressed your need for a buttermilk substitute for pancakes.

## Success judgment
The chatbot helped if it gave a specific substitute (e.g., 1 cup milk + 1 tbsp lemon juice) and explained how to adjust for fluffiness and tanginess, leaving you confident to proceed.
