# Finance Chatbot

## Your situation
You are looking for a mortgage. Share your price range down payment and credit profile.

## Your goal
Get a specific mortgage recommendation for a $350k home with a $70k down payment and a 720 credit score.

## Constraints on your behavior
["- Start by stating you're looking for a mortgage but don't immediately share all details; reveal price range first, then down payment, then credit score as the conversation progresses.", '- Push back if the chatbot gives generic advice without specific numbers or loan options.', '- Mention you prefer a fixed-rate mortgage and want to know about current interest rates and monthly payments.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when you receive a concrete mortgage recommendation (loan type, rate, monthly payment) based on the $350k price, $70k down payment (20%), and 720 credit score, OR after 5 chatbot turns without a specific answer.

## Success judgment
The chatbot provided a specific mortgage option (e.g., 30-year fixed, 6.5% APR, $1,770 monthly) using the $350k price, $70k down payment, and 720 credit score. If it only gave general advice or failed to use all variables, it did not succeed.
