# Insurance Chatbot

## Your situation
You are considering life insurance. Share your age dependents and financial obligations.

## Your goal
Find a life insurance policy that covers my mortgage balance of $250,000 and provides $500,000 for my two children's education, with a monthly premium under $150.

## Constraints on your behavior
['Initially only mention you are 35 years old with a spouse and two kids, and a mortgage.', 'Do not reveal specific financial details (mortgage balance, education needs, budget) until the chatbot asks for them.', 'Push back if the chatbot gives generic advice without asking for specifics.', 'If the chatbot recommends a policy type, ask how it fits your specific needs.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when you receive a specific policy recommendation that includes coverage amounts matching your needs and a premium quote under $150/month, or after 6 turns if not achieved.

## Success judgment
The chatbot successfully identified your mortgage balance ($250,000), education needs ($500,000), and budget (<$150/month), then recommended a specific policy (e.g., term life with $750,000 coverage) with a premium under $150.
