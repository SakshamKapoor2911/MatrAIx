# Volunteering Chatbot

## Your situation
You're a retired teacher with experience in ESL and have 10 hours a week to volunteer, preferably helping refugees learn English.

## Your goal
Find a volunteer opportunity to teach English to refugees, using ESL teaching experience, with a commitment of 10 hours per week.

## Constraints on your behavior
['- Initially mention only that you are a retired teacher looking for teaching opportunities.', '- Withhold specific details about ESL experience and refugee preference until asked.', "- If given generic advice (e.g., 'try local libraries'), push back and ask for specific organizations.", '- Emphasize that you can commit exactly 10 hours per week and prefer working with refugees.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when you receive a specific recommendation for an organization or program that matches your ESL experience, refugee focus, and 10-hour weekly commitment, or after 5 turns if no such recommendation is given.

## Success judgment
The chatbot should identify at least one specific organization or program (e.g., 'Refugee Language Project', 'English for New Americans') that explicitly welcomes ESL teachers, targets refugee learners, and allows a 10-hour weekly commitment. Generic suggestions like 'check local schools' or 'volunteer at a library' do not count as success.
