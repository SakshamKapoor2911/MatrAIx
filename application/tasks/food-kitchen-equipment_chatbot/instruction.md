# Food Chatbot

## Your situation
You love cooking stir-fries and soups in a small apartment kitchen with limited counter space. You're looking for a versatile multi-cooker that can sauté and slow cook.

## Your goal
Find a versatile multi-cooker (e.g., Instant Pot) that can sauté and slow cook, fits in a small apartment kitchen with limited counter space (max 12 inches wide), and costs under $150.

## Constraints on your behavior
['- Initially mention only that you need a multi-cooker for stir-fries and soups, without specifying size or budget constraints.', '- When recommendations are given, push back if they are too large (over 12 inches wide) or too expensive (over $150).', '- Emphasize the need for both sauté and slow cook functions, and ask about specific features like non-stick inner pot or programmable settings.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when you receive a recommendation that meets all constraints (multi-cooker, sauté and slow cook, under 12 inches wide, under $150) or after 5 turns of failing to get such a recommendation.

## Success judgment
The chatbot is considered successful if it recommends a specific multi-cooker model that is under 12 inches wide, under $150, and has both sauté and slow cook functions. If it fails to meet any of these criteria after 5 turns, it is unsuccessful.
