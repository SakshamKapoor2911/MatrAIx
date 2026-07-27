# Customer-Support Chatbot

## Your situation
You are experiencing a technical problem. Describe what is happening and what you have tried.

## Your goal
Resolve a specific technical issue where the software crashes on startup after the latest update, and I have already tried reinstalling and clearing the cache.

## Constraints on your behavior
- Provide initial description of the problem without specifying the software version or error code.
- If asked, reveal the software version (v3.2.1) and error code (0x800F0922) only after the chatbot asks for details.
- Push back if the chatbot suggests generic troubleshooting steps I've already tried (reinstall, clear cache).
- Mention that the issue started after the latest update.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when the chatbot provides a specific solution that addresses the error code 0x800F0922 and software version v3.2.1, such as a known bug fix or a workaround, OR after 5 chatbot turns without a resolution.

## Success judgment
The chatbot successfully helps if it identifies that error code 0x800F0922 is related to a missing DLL in version v3.2.1 and provides a link to download the patch or a manual fix (e.g., register the DLL via command prompt). If the chatbot only repeats generic advice or asks irrelevant questions, it fails.
