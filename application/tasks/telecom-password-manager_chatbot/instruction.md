# Telecom Chatbot

## Your situation
You use the same password for everything and got a notification that one of your accounts was compromised.

## Your goal
Get clear, actionable steps to secure my telecom account and a recommendation for a password manager that works with my existing devices, plus confirmation that changing my telecom password won't lock me out of other services.

## Constraints on your behavior
- Open by describing your situation: 'I got a notification that one of my accounts was compromised, and I use the same password for everything. I'm worried about my telecom account.' Don't reveal you need help with a password manager until the chatbot asks a follow-up or gives generic advice like 'change your password.'
- If the chatbot gives generic advice like 'use a strong password,' push back: 'But I have trouble remembering different passwords. How can I manage that?'
- Mention you have an Android phone and a Windows laptop, and ask if the recommended password manager syncs across them.
- Say you're on a tight budget, so free options are preferred.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot gives you a specific password manager name (e.g., Bitwarden, LastPass) that syncs across Android and Windows, and explains how to change your telecom password without affecting other accounts, OR (b) after 5 exchanges the chatbot has still not addressed your specific device compatibility or budget constraints.

## Success judgment
The chatbot helped if its advice referenced your specific devices (Android phone and Windows laptop) and budget (free or low-cost), and you left with an actionable first step you could take, such as installing a specific password manager or changing your telecom password with a recovery method in place.
