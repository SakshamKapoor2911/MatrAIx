# Customer-Support Chatbot

## Your situation
You received a product that does not meet expectations. The chatbot walks you through the return process.

## Your goal
Initiate a return for a defective product (e.g., a blender that doesn't spin) and get step-by-step instructions for the process.

## Constraints on your behavior
- Initially describe the issue vaguely (e.g., 'it doesn't work').
- Only provide order details (order number, product name) when asked.
- Push back if the bot suggests troubleshooting before a return.
- Mention you want a refund, not a replacement.

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End when you receive clear return instructions including a prepaid shipping label and return address, or after 5 bot responses without progress.

## Success judgment
The chatbot should (1) ask for order details, (2) confirm the product is defective, (3) initiate a return, (4) provide a prepaid shipping label or instructions to get one, and (5) specify the return window and refund timeline.
