# Insurance Chatbot

## Your situation
You just adopted a 2-year-old Labrador retriever and want to cover potential accidents and illnesses.

## Your goal
Get a pet insurance policy that covers accidents and illnesses for a 2-year-old Labrador retriever, with monthly premiums under $50 and a deductible under $250.

## Constraints on your behavior
['- Start by asking for general coverage options for dogs, but do not reveal the breed or age until asked.', '- Push back if the agent suggests a plan with a waiting period longer than 14 days for accidents.', '- Mention the monthly budget of $50 and deductible preference of $250 only if the initial options are too expensive.', '- Ask about coverage for hereditary conditions common in Labradors (e.g., hip dysplasia) if not mentioned.']

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End when a specific policy is recommended that meets all constraints (accident/illness coverage, premium ≤ $50, deductible ≤ $250, waiting period ≤ 14 days) or after 8 total messages without a suitable option.

## Success judgment
The chatbot provided a policy name with monthly premium ≤ $50, deductible ≤ $250, covers accidents and illnesses, waiting period ≤ 14 days, and addressed hereditary conditions (hip dysplasia) either included or excluded explicitly.
