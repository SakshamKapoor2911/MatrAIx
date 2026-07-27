# Finance Chatbot

## Your situation
You are planning for retirement. Share your age current savings and target retirement age.

## Your goal
Get personalized retirement savings advice to determine if current savings of $500,000 at age 45 is on track to retire at age 65.

## Constraints on your behavior
- Start by stating age 45 and current savings of $500,000 but do not immediately reveal target retirement age; wait for chatbot to ask.
- If chatbot gives generic advice (e.g., 'save more'), push back and ask for specific calculations or projections.
- Mention that you are risk-averse and prefer conservative investment options.
- Do not accept advice that requires high-risk investments.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End conversation when you receive a clear answer on whether $500,000 at age 45 is sufficient for retirement at age 65, with a suggested monthly savings target and conservative portfolio allocation.

## Success judgment
The chatbot should: (1) ask for target retirement age, (2) compute the required savings using reasonable assumptions (e.g., 4% withdrawal rate, 5% annual return, 2% inflation), (3) provide a specific monthly savings amount, and (4) recommend a conservative asset allocation (e.g., 60% bonds, 40% stocks). If the chatbot fails to ask for age, uses unrealistic assumptions, or gives generic advice without numbers, it fails.
