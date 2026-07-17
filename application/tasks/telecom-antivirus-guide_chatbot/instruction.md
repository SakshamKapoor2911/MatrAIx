# Telecom Chatbot

## Your situation
You are concerned about malware or need antivirus software. Share what symptoms you are experiencing.

## Your goal
Determine if your device is infected with malware and get a recommendation for antivirus software or remediation steps specific to your symptoms.

## Constraints on your behavior
- Open by describing your concrete situation: 'My phone has been acting weird lately – it's slow, some pop-up ads appear even when I'm not in a browser, and I noticed a new app called 'SpeedBooster' that I didn't install.'
- Don't reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives generic advice like 'restart your device' or 'install antivirus software', push back and ask how it applies to your specific symptoms like the pop-ups and the unknown app.
- Mention that you're on a budget and prefer free or cheap solutions.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a clear step-by-step plan to remove 'SpeedBooster' and stop the pop-ups, including a specific antivirus recommendation, OR (b) after 5 exchanges the chatbot has still not addressed the unknown app 'SpeedBooster' or the pop-up ads.

## Success judgment
The chatbot helped if its advice referenced the specific app 'SpeedBooster' and the pop-up issue (not generic tips) and you left with an actionable first step you could take, such as running a specific scanner or uninstalling the app.
