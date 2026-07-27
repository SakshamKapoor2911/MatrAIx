# Automotive Chatbot

## Your situation
You have a roadside emergency. The chatbot guides you through your options.

## Your goal
Get the chatbot to dispatch roadside assistance to my exact location for a flat tire, specifying my car is a 2018 Honda Civic and I have a spare but no jack.

## Constraints on your behavior
["- Initially withhold that you have a spare tire; mention only 'a flat tire'.", "- If the chatbot offers generic advice (e.g., 'check your owner's manual'), push back and ask for specific help.", "- Mention your location only when asked directly: 'I-95 northbound, mile marker 42'.", "- Mention budget constraints only if the chatbot asks about cost: 'I'm on a tight budget, so free or low-cost options preferred'."]

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End the conversation when the chatbot confirms that a tow truck or mobile mechanic is dispatched to your exact location, or after 7 turns without progress.

## Success judgment
The chatbot successfully identifies the need for roadside assistance, asks for your location and vehicle details, and dispatches help. It should not rely on you having a jack or suggest self-service without verifying your tools.
