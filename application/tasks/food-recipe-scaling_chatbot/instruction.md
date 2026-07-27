# Food Chatbot

## Your situation
You need to adjust a recipe for a different number of servings. Share the original quantities.

## Your goal
Get the recipe for chocolate chip cookies adjusted from 24 servings to 12 servings, with original quantities of 2 cups flour, 1 cup butter, 1 cup sugar, 2 eggs.

## Constraints on your behavior
['Start by stating the original recipe and the desired serving size without giving the new quantities.', 'If the chatbot asks for specific ingredients, provide them one at a time.', 'Do not accept generic scaling advice; insist on exact adjusted measurements.', 'If the chatbot provides a scaled recipe, verify the math (e.g., halving each ingredient).']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when the chatbot provides the exact adjusted quantities for all four ingredients (flour, butter, sugar, eggs) that are correctly halved, or after 6 messages if the chatbot fails to give a complete answer.

## Success judgment
The chatbot succeeded if it outputs: flour: 1 cup, butter: 1/2 cup, sugar: 1/2 cup, eggs: 1 egg (or equivalent). Failure if it only gives a scaling factor without specific numbers, or if any ingredient is missing or miscalculated.
