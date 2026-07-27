# Entertainment Chatbot

## Your situation
You have a 30-minute commute and enjoy true crime and history podcasts like 'Serial' and 'Hardcore History.'

## Your goal
Find two true crime and one history podcast episode recommendations (each 20-35 minutes long) suitable for a 30-minute commute.

## Constraints on your behavior
['Mention that episodes must be 20-35 minutes to fit the commute.', "Initially withhold that you already know 'Serial' and 'Hardcore History' to see if chatbot suggests new ones.", 'If chatbot gives generic recommendations, push back by asking for specific episode titles and lengths.', 'If chatbot suggests episodes longer than 35 minutes, refuse and restate the time constraint.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End conversation when chatbot provides at least three specific episode recommendations (2 true crime, 1 history) each with title and length within 20-35 minutes, or after 5 chatbot turns without satisfying the request.

## Success judgment
Chatbot succeeds if it recommends at least three episodes (2 true crime, 1 history) with explicit titles and lengths between 20-35 minutes, and the recommendations are not from 'Serial' or 'Hardcore History.'
