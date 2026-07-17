# Customer-Support Chatbot

## Your situation
You have a gift card and need help with balance check or redemption.

## Your goal
Check the remaining balance on your gift card and redeem it for a specific item (a $50 e-book reader) from the online store.

## Constraints on your behavior
- Open by describing that you have a gift card and want to check its balance, but do not mention the e-book reader until the chatbot asks for details or gives generic redemption steps.
- If the chatbot gives generic advice like 'enter the card number on the checkout page', push back by saying 'I already tried that, but it didn't work. The card might have a different balance, or maybe I need to check first.'
- Mention that you are on a tight budget and need to ensure the card covers the full cost of the item before proceeding.
- If the chatbot asks for the card number, provide it only after they ask for it.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot tells you the exact remaining balance (e.g., $45.30) and confirms that the e-book reader ($50) would require an additional payment of $4.70, OR (b) after 5 exchanges the chatbot has still not provided the specific balance or redemption steps for your gift card.

## Success judgment
The chatbot helped if it provided the specific balance of your gift card and gave clear instructions on how to redeem it for the e-book reader, including any partial payment needed.
