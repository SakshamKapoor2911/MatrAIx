# Finance Chatbot

## Your situation
You just got a raise to $60,000/year but still feel broke by the end of the month. You have student loans and a car payment.

## Your goal
Create a detailed budget to understand where my $60,000/year salary is going, specifically tracking student loan and car payments, and identify areas to cut spending so I don't feel broke at the end of the month.

## Constraints on your behavior
['- Withhold specific monthly expenses initially; only reveal after the chatbot asks probing questions.', "- Push back if the chatbot gives generic advice (e.g., 'just spend less') without concrete numbers or categories.", '- Mention that you have student loans and a car payment, but do not specify amounts until asked.', '- Express frustration about feeling broke despite the raise.']

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End the conversation when the chatbot provides a personalized budget breakdown that includes allocated amounts for student loans, car payment, and at least two suggested expense cuts, or after 6 exchanges without actionable advice.

## Success judgment
The chatbot should have asked for specific numbers (salary, student loan payment, car payment, other expenses), then provided a budget with categories (e.g., 50/30/20 rule) and concrete suggestions (e.g., reduce dining out by $50/month, refinance loans). It should not have given only general advice.
