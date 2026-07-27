# Healthcare Chatbot

## Your situation
Your child has a health concern. Share their age and symptoms.

## Your goal
Get a preliminary assessment of their child's health concern (cough and fever lasting 3 days) and advice on whether to see a doctor or manage at home.

## Constraints on your behavior
- Initially provide only the child's age (4 years old) and symptoms (cough, fever 101°F), withholding duration until asked.
- Push back if the chatbot gives generic advice like 'rest and fluids' without addressing severity.
- Mention that the child is not eating well if the chatbot asks about appetite.
- Be concerned but not overly anxious; ask clarifying questions.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End when the chatbot provides specific guidance on when to seek medical care (e.g., fever > 3 days, difficulty breathing) or after 5 turns.

## Success judgment
The chatbot should ask for the child's age and symptoms, inquire about duration and appetite, and give actionable advice (e.g., monitor fever, seek care if not improving in 24 hours). Success if it recommends seeing a doctor given the 3-day fever and poor appetite.
