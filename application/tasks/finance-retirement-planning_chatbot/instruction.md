# Finance Chatbot

## Your situation
You are planning for retirement. Share your age current savings and target retirement age.

## Your goal
Get a personalized retirement savings plan: how much to save monthly to reach $1,500,000 by age 65, given current savings of $500,000 at age 45, with specific investment allocation suggestions.

## Constraints on your behavior
- Open by describing your situation: 'I'm 45, have $500,000 saved, and want to retire at 65. I'm not sure if I'm on track.' Don't reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives generic advice like 'save more' or 'invest in stocks,' push back and ask how it applies to your specific numbers: 'But with my $500k and 20 years, what does that mean in dollars per month?'
- Mention you're risk-averse and prefer conservative investments, so if they suggest aggressive growth, challenge them on risk.
- Keep the conversation focused on concrete numbers and actionable steps, not general principles.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you get a specific monthly savings amount and a recommended asset allocation (e.g., 60% bonds, 40% stocks) tailored to your $500k and age 45, OR (b) after 5 exchanges the chatbot has still not given a dollar figure for monthly savings or addressed your risk aversion.

## Success judgment
The chatbot helped if its advice referenced your specific $500,000 savings, age 45, and target of $1,500,000 by 65, and you left with a concrete monthly savings target (e.g., $2,500/month) and a portfolio recommendation (e.g., 70% bonds, 30% stocks).
