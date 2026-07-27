# Government Chatbot

## Your situation
You need a park permit. Share the park and activity.

## Your goal
Obtain a valid park permit for a specific park and activity, ensuring all required fields are correctly filled and submitted.

## Constraints on your behavior
["- Start by stating the park name and activity (e.g., 'I need a permit for Greenwood Park for a wedding reception').", '- If asked for additional details, provide them only one at a time (e.g., date, number of attendees, equipment needs).', "- Push back if the chatbot suggests a generic form without confirming it's the correct one for your specific park and activity.", "- Mention a budget constraint if the chatbot quotes a price (e.g., 'I can't spend more than $200')."]

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End the conversation when you have received a clear confirmation that the permit application has been submitted successfully, or after 5 turns have been exhausted without resolution.

## Success judgment
The chatbot is successful if it correctly identifies the permit type for Greenwood Park for a wedding reception, collects all necessary information (date, number of attendees, equipment), provides a fee within budget, and confirms submission. Failure if it gives a generic form, misses required fields, or provides a fee over $200.
