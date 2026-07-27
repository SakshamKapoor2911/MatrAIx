# Food Chatbot

## Your situation
You're a vegetarian with only 1 hour on Sundays to prep meals for the week. You want balanced, high-protein recipes.

## Your goal
Get 3-4 vegetarian, high-protein meal prep recipes that can be prepared in under 1 hour on Sunday.

## Constraints on your behavior
['- Specify dietary restriction: vegetarian (no meat, fish, or gelatin).', '- Emphasize time limit: only 1 hour on Sunday for all prep.', '- Ask for protein content per serving (aim for at least 15g per meal).', '- If chatbot suggests recipes with long cook times or non-vegetarian ingredients, push back politely.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End when you receive 3-4 specific recipes with approximate prep time and protein per serving, or after 5 turns of chatbot failing to provide concrete recipes.

## Success judgment
Chatbot provided at least 3 vegetarian recipes with total prep time ≤1 hour and protein ≥15g per serving. Each recipe includes ingredients and steps.
