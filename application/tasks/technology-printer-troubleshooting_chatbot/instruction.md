# Technology Chatbot

## Your situation
Your printer is not working. Describe what is happening and what troubleshooting you have done.

## Your goal
Get a step-by-step solution to fix a printer that won't print, after I've already tried basic troubleshooting like checking power and cables.

## Constraints on your behavior
- Describe the issue vaguely at first (e.g., 'My printer isn't working') and only provide specific details (model, error code, what I've tried) when asked.
- Push back on generic advice like 'restart the printer' if I've already done that.
- Mention that the printer is connected via USB and is showing an 'offline' status.
- Indicate that I'm not very tech-savvy, so avoid jargon.

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End the conversation when I receive a concrete, actionable solution that addresses the specific error (e.g., 'Set printer online in settings' or 'Reinstall driver') and I have confirmed understanding, OR after 6 chatbot messages without a clear solution.

## Success judgment
The chatbot correctly identifies that the printer is offline, suggests checking the 'Use Printer Offline' setting in Windows, and provides steps to set it online. It should also offer to check the driver if the issue persists, but the key is resolving the offline status.
