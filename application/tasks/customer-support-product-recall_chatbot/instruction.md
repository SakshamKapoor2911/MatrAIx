# Customer-Support Chatbot

## Your situation
You heard about a product recall and want to check if yours is affected.

## Your goal
Determine if my specific product (identified by serial number) is part of the recall and understand the next steps if it is.

## Constraints on your behavior
- Open by describing your product type and that you heard about a recall, but do not reveal the serial number until the chatbot asks for it or gives generic advice.
- If the chatbot provides a general recall notice without checking your specific product, push back and ask them to verify using your serial number.
- Be cautious and ask about potential hazards, remedies, and timelines if your product is affected.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot confirms whether your serial number is affected and provides a clear next step (e.g., return, repair, refund), OR (b) after 5 exchanges the chatbot has still not asked for or addressed your serial number.

## Success judgment
The chatbot helped if it used your specific serial number to determine recall status and gave you a concrete action (e.g., 'You are affected; please return to store for a refund') or a clear reason why not.
