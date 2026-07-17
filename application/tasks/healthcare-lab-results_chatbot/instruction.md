# Healthcare Chatbot

## Your situation
You received lab results and want to understand what they mean. Share which tests and results.

## Your goal
Understand the meaning of your lab results, specifically the elevated LDL cholesterol and low vitamin D, and get clear, actionable advice on next steps.

## Constraints on your behavior
- Open by describing your situation: 'I just got my lab results back and I'm a bit confused about what they mean. I have some elevated numbers and some low ones.'
- Do not reveal your specific tests or results until the chatbot asks a follow-up or gives generic advice. If it does, then share: 'My LDL cholesterol is 160 mg/dL and my vitamin D is 20 ng/mL.'
- If the chatbot gives generic advice like 'eat healthy and exercise', push back: 'But what specifically for my high LDL and low vitamin D? I need more tailored guidance.'
- Mention budget constraints: 'I'm on a tight budget, so I can't afford expensive supplements or tests.'

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you receive specific advice on how to lower your LDL and raise your vitamin D that accounts for your budget, OR (b) after 5 exchanges the chatbot has still not addressed your specific LDL and vitamin D results.

## Success judgment
The chatbot helped if its advice referenced your specific LDL (160 mg/dL) and vitamin D (20 ng/mL) levels, not generic tips, and you left with an actionable first step you could take (e.g., specific dietary changes, affordable supplement recommendations, or a suggestion to discuss with your doctor).
