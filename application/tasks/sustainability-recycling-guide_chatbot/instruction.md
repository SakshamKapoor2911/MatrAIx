# Sustainability Chatbot

## Your situation
You're unsure if pizza boxes, plastic bags, and glass jars can go in your curbside bin. Your local program is confusing.

## Your goal
Determine whether pizza boxes, plastic bags, and glass jars are accepted in your curbside recycling bin.

## Constraints on your behavior
- Start by vaguely describing the items without naming them (e.g., 'I have some food containers, plastic wraps, and glass containers'). 
- If the chatbot gives generic advice, push back by mentioning your local program is confusing. 
- Only reveal the specific items (pizza boxes, plastic bags, glass jars) after the chatbot asks clarifying questions or provides initial guidance.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when you receive a clear, item-by-item answer for pizza boxes, plastic bags, and glass jars, or after 5 chatbot turns without a satisfactory answer.

## Success judgment
The chatbot successfully identifies that pizza boxes (if greasy) may not be recyclable, plastic bags often are not accepted curbside (require drop-off), and glass jars are typically accepted but may need rinsing. It provides specific guidance based on these items, not generic recycling tips.
