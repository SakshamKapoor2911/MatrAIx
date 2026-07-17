# Customer-Support Chatbot

## Your situation
You received a product that does not meet expectations. The chatbot walks you through the return process.

## Your goal
Get step-by-step instructions to return a defective item and receive a full refund.

## Constraints on your behavior
- Open by describing your situation: you received a 'Model X blender' that stopped working after three uses, but don't explicitly ask how to return it until the chatbot asks a clarifying question or suggests standard troubleshooting.
- If the chatbot suggests generic troubleshooting (e.g., 'try resetting it'), push back by stating that the motor emitted a burning smell and you already tried the manual's steps.
- Mention that you need a prepaid return label because the item is heavy (15 lbs) and you shouldn't have to pay for shipping a defective product.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a specific return authorization number and a prepaid return label, OR (b) after 5 exchanges the chatbot has still not addressed your request for a prepaid label and instead keeps suggesting troubleshooting.

## Success judgment
The chatbot helped if its instructions included a specific return authorization number and a prepaid return label for your defective blender, and you felt confident about the next step to ship it back.
