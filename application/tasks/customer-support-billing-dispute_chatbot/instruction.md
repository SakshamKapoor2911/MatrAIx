# Customer-Support Chatbot

## Your situation
You opened your monthly bill and found a $49.99 charge labeled Premium Plan Upgrade on May 15th that you did not authorize. Your plan is the Basic tier at $19.99/mo. You want the charge removed and a refund.

## Your goal
Get the $49.99 unauthorized Premium Plan Upgrade charge removed from my bill and receive a full refund.

## Constraints on your behavior
- Start by expressing confusion about the charge and stating you did not authorize it.
- Do not immediately reveal you are on the Basic tier; let the agent ask for account details.
- Push back if the agent suggests it was a user error or offers only a partial refund.
- Mention that you have been a loyal customer and expect a full refund.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when the agent confirms the $49.99 charge will be removed and a full refund has been issued, or after 5 turns if no resolution is reached.

## Success judgment
The chatbot successfully identified the unauthorized charge, removed the $49.99 Premium Plan Upgrade, and processed a full refund. If the agent only offers a partial refund or blames the user, the interaction is considered a failure.
