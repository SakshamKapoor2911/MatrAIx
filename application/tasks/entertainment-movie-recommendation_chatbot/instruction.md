# Entertainment Chatbot

## Your situation
You're in the mood for a comedy with a rating above 7 on IMDb, and you have Netflix and Hulu.

## Your goal
Find a comedy movie available on Netflix or Hulu with an IMDb rating above 7.

## Constraints on your behavior
['- Initially only state you want a comedy movie, without specifying platforms or rating.', '- If asked for preferences, mention Netflix and Hulu as your available platforms.', '- Insist on IMDb rating above 7; reject any suggestions below 7.', '- If the chatbot suggests a movie not on your platforms, ask for alternatives.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End when you receive a specific movie title that is a comedy, has IMDb rating above 7, and is available on Netflix or Hulu.

## Success judgment
The chatbot succeeded if it recommended at least one movie that is a comedy, IMDb rating > 7, and available on Netflix or Hulu. If it failed to meet all three criteria, it failed.
