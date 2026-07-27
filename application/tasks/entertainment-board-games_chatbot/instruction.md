# Entertainment Chatbot

## Your situation
Your game night group has 4-6 players who enjoy strategy games like Settlers of Catan but want something with more depth and a fantasy theme.

## Your goal
Find a fantasy-themed strategy board game for 4-6 players that offers more depth than Settlers of Catan, with a concrete recommendation including game name, player count, and complexity level.

## Constraints on your behavior
['Begin by stating the group size (4-6) and preference for fantasy theme and deeper strategy than Catan, without mentioning specific game names initially.', 'Push back if the chatbot suggests party games, games for fewer players, or games without a fantasy theme.', 'If the chatbot asks for more preferences, mention that you like resource management, variable player powers, and a playtime under 3 hours.', "Stay focused on finding a single concrete recommendation; do not accept vague suggestions like 'any game from this list'."]

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when the chatbot provides a specific game name (e.g., 'Terra Mystica', 'Scythe', 'Blood Rage') that fits the criteria, or after 5 turns if no concrete recommendation is given.

## Success judgment
The chatbot succeeds if it recommends a specific fantasy strategy game for 4-6 players with more depth than Catan, such as 'Terra Mystica' (fantasy, 2-5 players but can be scaled), 'Scythe' (alternate history with fantasy elements, 1-5 players), or 'Blood Rage' (mythological fantasy, 2-4 players). The recommendation must explicitly address player count and complexity relative to Catan. Failure includes recommending games for wrong player counts (e.g., 2-4), non-fantasy themes, or games with similar depth to Catan.
