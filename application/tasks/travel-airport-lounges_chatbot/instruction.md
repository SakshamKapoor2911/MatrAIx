# Travel Chatbot

## Your situation
You have a layover or want lounge access. Share your airport and travel class.

## Your goal
Find out if you can access an airport lounge during your layover at Frankfurt Airport (FRA) while traveling in economy class.

## Constraints on your behavior
['- Start by stating you have a layover at FRA and ask about lounge access.', '- Initially withhold that you are in economy class; only reveal it if the chatbot asks or if you need to clarify.', '- Push back if the chatbot gives generic advice without considering your specific airport and class.', "- If the chatbot suggests paid options, ask about cost and whether it's worth it for a short layover."]

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when you receive a clear answer about lounge access for economy class at FRA (including any paid options or alternative solutions) or after 5 exchanges without resolution.

## Success judgment
The chatbot correctly identifies that economy class passengers typically do not have complimentary lounge access at FRA, and provides viable alternatives such as paid lounge access (e.g., Priority Pass, walk-in rates) or other amenities (e.g., rest zones, cafes).
