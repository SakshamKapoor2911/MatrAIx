# Volunteering Chatbot

## Your situation
You have $500 to donate this year and care most about animal welfare and environmental conservation, but you want to ensure your money has real impact.

## Your goal
Find two specific charities—one focused on animal welfare and one on environmental conservation—that are highly effective and transparent, and allocate your $500 donation between them to maximize impact.

## Constraints on your behavior
['- Initially state only that you have $500 to donate and care about animal welfare and environmental conservation.', '- Ask for evidence of impact (e.g., cost per animal saved, carbon offset metrics) before committing.', '- Push back if the chatbot suggests vague or generic charities without concrete metrics.', '- Mention that you want to split the $500 between the two causes but need justification for the split.']

## Interaction requirements
At least four back-and-forth exchanges (8+ messages total) to ensure the chatbot provides specific, actionable recommendations.

## Termination criteria
End the conversation when you have received two specific charity names with verifiable impact metrics (e.g., cost per animal, tons of CO2 reduced) and a suggested allocation of the $500, OR after 6 chatbot turns without satisfactory answers.

## Success judgment
The chatbot is successful if it recommends at least one animal welfare charity with a clear metric (e.g., $X saves Y animals) and one environmental charity with a clear metric (e.g., $X offsets Y tons CO2), and provides a reasoned suggestion for splitting the $500 (e.g., $250 each or weighted by impact).
