# Insurance Chatbot

## Your situation
Your business may need cyber insurance. Share your business type and data handling.

## Your goal
Determine if the business needs cyber insurance based on its type (e-commerce) and data handling (customer PII stored).

## Constraints on your behavior
['Start with generic business type (e-commerce) and only reveal specific data handling (customer PII) if asked.', 'Push back on one-size-fits-all advice by asking for specifics about coverage for data breach costs.', 'Mention budget constraint: monthly premium under $200.', 'Do not volunteer the number of customer records unless asked.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End when the chatbot provides a specific recommendation (e.g., a policy name) that covers data breach response, or after 5 turns if no actionable answer.

## Success judgment
The chatbot successfully identifies the e-commerce business storing customer PII, recommends a specific cyber insurance policy (e.g., 'CyberGuard Pro') that includes data breach coverage, and quotes a premium under $200/month.
