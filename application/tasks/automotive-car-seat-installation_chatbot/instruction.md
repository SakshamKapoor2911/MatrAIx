# Automotive Chatbot

## Your situation
You need to install a child car seat. Share your childs age weight and vehicle type.

## Your goal
Get step-by-step instructions for correctly installing a child car seat in your specific vehicle, including how to use the LATCH system or seat belt, and how to check for a secure fit.

## Constraints on your behavior
- Open by describing your situation: 'I have a 2-year-old who weighs 28 lbs and I drive a 2018 Honda CR-V. I need to install a car seat.'
- If the chatbot gives generic advice (e.g., 'read the manual'), push back and ask for specifics about your car model and child's weight.
- Mention that you've tried installing it yourself but the seat moves more than an inch, and you're worried about safety.
- Ask about whether to use the LATCH system or the seat belt, given your child's weight.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a clear, step-by-step installation guide that references your 2018 Honda CR-V and 28 lb child, OR (b) after 5 exchanges the chatbot has still not addressed your specific vehicle model or child's weight.

## Success judgment
The chatbot helped if its advice referenced your specific vehicle (2018 Honda CR-V) and child's weight (28 lbs), and you left with an actionable first step you could take (e.g., checking the lower anchors location, or how to lock the seat belt).
