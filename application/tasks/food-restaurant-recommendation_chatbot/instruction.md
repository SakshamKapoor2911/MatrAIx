# Food Chatbot

## Your situation
It's your anniversary and you want a romantic Italian dinner in downtown Chicago for under $100 per person.

## Your goal
Find a romantic Italian restaurant in downtown Chicago for an anniversary dinner, with a total cost under $100 per person (including tax and tip).

## Constraints on your behavior
- Initially state only the desire for a romantic Italian dinner in downtown Chicago.
- Push back if the chatbot suggests non-Italian cuisines or locations outside downtown.
- Mention the $100 per person budget only after the chatbot proposes options, to test if it can tailor recommendations.
- Ask about ambiance (e.g., candlelight, quiet) and any special anniversary offerings (e.g., complimentary dessert).

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End the conversation when the chatbot provides at least one specific restaurant recommendation that meets all criteria: Italian, downtown Chicago, under $100 per person, and romantic ambiance (e.g., candlelit, quiet). If the chatbot fails to meet these after 8 exchanges, terminate with a statement that the recommendations are not suitable.

## Success judgment
Success if the chatbot recommends at least one specific Italian restaurant in downtown Chicago with an estimated per-person cost under $100 (including tax/tip) and described as romantic (e.g., candlelit, quiet, anniversary-friendly). Failure if the chatbot suggests non-Italian, outside downtown, over budget, or generic recommendations without cost/ambiance details.
