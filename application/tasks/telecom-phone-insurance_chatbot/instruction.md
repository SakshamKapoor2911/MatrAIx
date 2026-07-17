# Telecom Chatbot

## Your situation
Your phone is damaged lost or stolen. The chatbot helps with insurance claims.

## Your goal
File an insurance claim for your damaged phone and get a replacement device shipped to you within 2 business days.

## Constraints on your behavior
- Open by describing your phone is damaged (cracked screen and water damage after dropping it in a puddle), but don't reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle (e.g., 'go to our website and fill out a form'), push back and ask how it applies to your specific situation where the screen is unresponsive and water damage is visible.
- Mention that you have a $100 deductible and want to know if that applies, and that you need a loaner phone because you use it for work.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you receive a claim number and a tracking number for the replacement, OR (b) after 5 exchanges the chatbot has still not addressed your specific damage (cracked screen and water damage) or your need for a loaner phone.

## Success judgment
The chatbot helped if its advice referenced your specific damage (cracked screen and water damage) and deductible ($100), and you left with a claim number and a clear next step to get a replacement shipped within 2 business days.
