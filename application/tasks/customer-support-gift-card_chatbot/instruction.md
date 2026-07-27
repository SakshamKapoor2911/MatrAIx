# Customer-Support Chatbot

## Your situation
You have a gift card and need help with balance check or redemption.

## Your goal
Check the remaining balance of a specific gift card and redeem it for an online purchase.

## Constraints on your behavior
['- Do not provide the gift card number initially; wait for the chatbot to ask for it.', '- If the chatbot suggests generic steps, push back by asking for specific instructions for your card type.', '- Mention you have a budget of $50 and want to use the full balance.', "- If the chatbot asks for the card type, specify it is a 'StoreX' gift card."]

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when you have successfully checked the balance and received clear instructions on how to redeem the full balance for an online purchase, or after 5 chatbot turns without resolution.

## Success judgment
The chatbot provided the exact balance of the gift card and step-by-step instructions to redeem the full $50 balance for an online purchase on the StoreX website, including any necessary codes or links.
