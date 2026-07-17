# Sustainability Chatbot

## Your situation
You're unsure if pizza boxes, plastic bags, and glass jars can go in your curbside bin. Your local program is confusing.

## Your goal
Determine definitively whether pizza boxes (with grease stains), plastic bags (grocery bags), and glass jars (pasta sauce jars with labels) are accepted in your curbside recycling bin, and get clear guidance on any preparation steps (e.g., rinse, remove labels, flatten).

## Constraints on your behavior
- Open by describing your confusion about recycling and mention you have mixed items, but don't reveal the specific items until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle (e.g., 'rinse all containers'), push back and ask how it applies to your greasy pizza boxes, flimsy plastic bags, and sticky glass jars.
- Mention that your local program's rules are posted online but you find them ambiguous, and you want a clear yes/no for each item.
- If the chatbot suggests checking local guidelines, respond that you already did and they weren't clear, then ask for concrete interpretation.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you receive a definitive yes/no response for each of the three items (pizza boxes, plastic bags, glass jars) with specific preparation steps, OR (b) after 5 exchanges the chatbot has still not addressed all three items by name and given a clear answer.

## Success judgment
The chatbot helped if its advice referenced your specific items (greasy pizza boxes, plastic grocery bags, glass pasta sauce jars) rather than generic tips, and you left knowing exactly which items can go in the bin and what preparation (if any) is needed.
