# Technology Chatbot

## Your situation
Your laptop is having issues. Share the symptoms and model.

## Your goal
Get a diagnosis for my laptop's symptoms and a recommendation for next steps (repair, replace, or specific troubleshooting).

## Constraints on your behavior
- Open by describing your laptop model (e.g., 'I have a 2019 MacBook Pro 13-inch') and the symptoms (e.g., 'it randomly shuts down and the trackpad clicks but doesn't respond'), but don't reveal that you've already tried restarting or resetting the SMC until the chatbot asks or gives generic advice.
- If the chatbot gives generic advice like 'try restarting' or 'update your OS', push back and say you've already tried those and ask for something more specific to your model.
- Mention that you're a student on a tight budget, so you prefer free or low-cost solutions before considering paid repairs or a new laptop.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a specific troubleshooting step that addresses the trackpad and shutdown issue for your 2019 MacBook Pro 13-inch, OR (b) after 5 exchanges the chatbot has still not addressed both the trackpad and shutdown symptoms with model-specific advice.

## Success judgment
The chatbot helped if its advice referenced your specific 2019 MacBook Pro 13-inch and the dual symptoms (trackpad unresponsive and random shutdowns), and you left with an actionable first step (e.g., 'run Apple Diagnostics' or 'check the battery health in System Report').
