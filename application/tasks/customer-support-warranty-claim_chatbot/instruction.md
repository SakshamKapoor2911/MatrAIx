# Customer-Support Chatbot

## Your situation
Your product is malfunctioning. The chatbot helps file a warranty claim with required documentation.

## Your goal
File a warranty claim for a malfunctioning product (model X-200, serial number SN12345678) purchased on 2023-05-15, and get a list of required documentation (proof of purchase, photos of defect, and a brief description).

## Constraints on your behavior
- Start by describing the issue vaguely (e.g., 'my device is broken') without giving model/serial initially.
- Push back if the chatbot offers generic troubleshooting steps instead of warranty claim process.
- Only provide specific details (model, serial, purchase date) when explicitly asked.
- Mention urgency due to product being essential for work.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
Conversation ends when the chatbot provides a clear list of required documentation for the warranty claim and confirms the claim can be initiated, OR after 5 chatbot responses without resolution.

## Success judgment
Chatbot successfully identifies that the user wants to file a warranty claim, asks for necessary details (model, serial, purchase date), and provides a specific list of required documents (proof of purchase, photos of defect, description). The chatbot does not insist on troubleshooting steps after the user declines.
