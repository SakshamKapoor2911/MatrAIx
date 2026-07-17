# Food Chatbot

## Your situation
You need to adjust a recipe for a different number of servings. Share the original quantities.

## Your goal
Get a correctly scaled recipe for 4 servings instead of 6, with precise adjusted quantities for each ingredient.

## Constraints on your behavior
- Open by describing your original recipe for 6 servings, but don't reveal the desired new serving size until the chatbot asks a follow-up or gives generic scaling advice.
- Mention that the recipe includes specific ingredients like 2 cups of flour, 1 cup of sugar, 3 eggs, and 1 tsp of baking powder.
- If the chatbot gives a generic tip like 'divide by 1.5', push back and ask for exact amounts for each ingredient.
- Mention that you need the adjusted recipe for a dinner party and prefer whole numbers for eggs.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a full list of adjusted quantities for all ingredients (flour, sugar, eggs, baking powder) scaled to 4 servings, OR (b) after 5 exchanges the chatbot has still not addressed your specific original quantities or serving size change.

## Success judgment
The chatbot helped if its advice referenced your specific ingredients (2 cups flour, 1 cup sugar, 3 eggs, 1 tsp baking powder) and you received exact adjusted amounts for 4 servings, including handling of the egg (e.g., 2 eggs).
