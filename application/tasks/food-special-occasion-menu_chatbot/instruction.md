# Food Chatbot

## Your situation
You are hosting a special meal and need a menu. Share the occasion and guest preferences.

## Your goal
Plan a 3-course dinner menu for a 10th wedding anniversary celebration, accommodating one guest who is vegetarian and another who is gluten-intolerant, with a budget of $150 for ingredients.

## Constraints on your behavior
['- Initially state only that you need a menu for a special occasion, without revealing the anniversary or dietary restrictions until asked.', '- When dietary restrictions are mentioned, specify vegetarian and gluten-intolerant, and ask for options that can be modified.', '- Push back if the chatbot suggests dishes that are too expensive or difficult to prepare within your budget and cooking skill level.', '- Mention the budget of $150 only if the chatbot asks about budget or suggests expensive dishes.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when you receive a full 3-course menu (appetizer, main, dessert) that satisfies the dietary restrictions and budget, or after 5 turns of the chatbot failing to provide a suitable menu.

## Success judgment
The chatbot provided a specific 3-course menu (appetizer, main, dessert) that includes at least one vegetarian and one gluten-free option per course, with total ingredient cost under $150. The menu should be appropriate for a 10th anniversary (special, not too casual).
