# Insurance Chatbot

## Your situation
You're planning a $5,000 family trip to Europe and want coverage for trip cancellation and medical emergencies.

## Your goal
Get a clear recommendation for a travel insurance policy that covers trip cancellation (up to $5,000) and medical emergencies for your family trip to Europe, with specific details on coverage limits, exclusions, and cost.

## Constraints on your behavior
- Open by describing your planned $5,000 family trip to Europe and that you need coverage for trip cancellation and medical emergencies, but don't reveal your specific question about deductibles or pre-existing conditions until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle of top travel insurance companies, push back and ask how their policies apply to your specific trip cost and family composition (e.g., two adults, two children).
- Mention that you're on a budget and want to keep the premium under $200 total for the family.
- If the chatbot recommends a policy, ask about exclusions for pre-existing medical conditions and how trip cancellation due to work emergencies is handled.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a specific policy recommendation with coverage limits for trip cancellation and medical, and addresses your budget constraint of under $200, OR (b) after 5 exchanges the chatbot has still not addressed your specific trip cost of $5,000 and family composition.

## Success judgment
The chatbot helped if its advice referenced your specific trip cost ($5,000), family composition (2 adults, 2 children), and budget ($200), and you left with a clear policy name and understanding of what is covered for trip cancellation and medical emergencies.
