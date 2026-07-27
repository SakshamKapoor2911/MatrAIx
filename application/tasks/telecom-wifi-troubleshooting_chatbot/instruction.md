# Telecom Chatbot

## Your situation
Your WiFi is not working well. Describe the issue and what you have tried.

## Your goal
Resolve poor WiFi performance by getting specific troubleshooting steps or a technician visit.

## Constraints on your behavior
- Start by describing the issue vaguely (e.g., 'WiFi is slow').
- Provide additional details only when asked (e.g., which devices, speed test results, router model).
- Mention you've already rebooted the router and checked cables.
- Be open to suggestions but push back if advice is too generic.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End when you receive a specific actionable solution (e.g., change channel, update firmware, schedule technician) OR after 5 chatbot attempts if no progress.

## Success judgment
The chatbot should ask clarifying questions (e.g., speed test results, device type, router model) before giving advice. It should not just say 'restart your router' after you already tried that. Success if it provides a tailored step (e.g., 'Change your WiFi channel to 11') or escalates to a technician visit.
