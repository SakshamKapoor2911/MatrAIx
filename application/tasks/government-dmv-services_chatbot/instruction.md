# Government Chatbot

## Your situation
You need to handle a DMV task. Share your state and what you need to do.

## Your goal
Renew my driver's license in California and find out if I can do it online.

## Constraints on your behavior
['- Mention the state (California) only after the chatbot asks.', "- Specify that I need to renew my driver's license.", '- Push back if the chatbot gives generic advice without checking my state.', '- Mention that I have a valid passport as ID if asked.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End when the chatbot confirms whether online renewal is possible for California and provides the necessary steps or alternative options.

## Success judgment
The chatbot correctly identifies that California offers online renewal for eligible drivers, and provides specific steps (e.g., visit the CA DMV website, have a valid passport, pay the fee). Alternatively, if ineligible, it explains why and offers in-person or mail options.
