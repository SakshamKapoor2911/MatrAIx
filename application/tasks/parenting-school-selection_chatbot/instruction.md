# Parenting Chatbot

## Your situation
You are choosing a school for your child. Share their age and your priorities.

## Your goal
Find a school for my 5-year-old child that emphasizes outdoor play and social-emotional learning, with a maximum commute of 20 minutes.

## Constraints on your behavior
- Start by giving the child's age (5) and asking for general recommendations.
- Only mention the priority of outdoor play after the chatbot suggests a generic school.
- Push back if the chatbot recommends a school focused on academics without addressing social-emotional learning.
- Mention the commute constraint only after receiving a few suggestions.

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End the conversation when the chatbot provides a list of 2-3 specific school names that meet all criteria (age 5, outdoor play, social-emotional learning, ≤20 min commute), or after 5 exchanges if no suitable options are given.

## Success judgment
The chatbot successfully identifies at least one school that serves 5-year-olds, incorporates outdoor play and social-emotional learning in its curriculum, and is within a 20-minute commute from the user's unspecified location (assume reasonable default).
