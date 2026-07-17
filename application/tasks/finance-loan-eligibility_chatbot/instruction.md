# Finance Chatbot

## Your situation
You are considering a loan. Share the type amount and your financial situation.

## Your goal
Get a clear understanding of whether a $15,000 personal loan is feasible for you, given your current debt-to-income ratio and credit score, and learn the steps to apply if it is.

## Constraints on your behavior
- Open by describing your financial situation: you have a steady job with $4,000 monthly income, $500 monthly student loan payment, and a credit score of 680. Don't reveal your specific loan question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives generic advice like 'improve your credit score' without addressing your specific numbers, push back and ask how that applies to your 680 score and $15k loan request.
- Mention that you are concerned about the debt-to-income ratio and want to know if it's too high for the loan amount. Also, you have a budget constraint: you can afford a maximum monthly payment of $300.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot gives a specific answer about the feasibility of a $15,000 loan given your income of $4,000, student loan payment of $500, and credit score of 680, OR (b) after 5 exchanges the chatbot has still not addressed your specific debt-to-income ratio and budget constraint of $300 monthly payment.

## Success judgment
The chatbot helped if its advice referenced your specific income of $4,000, student loan payment of $500, credit score of 680, and monthly budget of $300, and you left with a clear actionable next step (e.g., 'you likely qualify, here's how to apply' or 'you need to lower your DTI first').
