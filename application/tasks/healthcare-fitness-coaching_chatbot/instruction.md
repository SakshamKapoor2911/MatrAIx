# Healthcare Chatbot

## Your situation
You've been sedentary for months and want to start running, but only have a pair of sneakers and a nearby park. Your goal is to run a 5K in 8 weeks.

## Your goal
Get a safe, progressive 8-week 5K training plan that uses only sneakers and a nearby park, including specific weekly run/walk intervals and rest days.

## Constraints on your behavior
['Initially mention only that you have sneakers and a park, but do not specify the 8-week goal until asked.', 'Push back on any equipment recommendations (e.g., fancy shoes, gym) by restating your limited resources.', "If the chatbot gives generic advice (e.g., 'start slow'), ask for concrete weekly schedules and distances.", 'Mention your sedentary history if the plan seems too aggressive.']

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total) to refine the plan.

## Termination criteria
End the conversation when you receive a detailed week-by-week plan with specific run/walk intervals, distances, and rest days that fits your 8-week timeline and equipment constraints.

## Success judgment
The chatbot succeeds if it provides a specific, progressive 8-week plan with weekly run/walk intervals (e.g., Week 1: 1 min run/2 min walk x 5, Week 2: 2 min run/2 min walk x 5, etc.), includes rest days, and does not require any equipment beyond sneakers and a park.
