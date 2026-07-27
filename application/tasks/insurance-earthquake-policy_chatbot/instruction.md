# Insurance Chatbot

## Your situation
You live in an earthquake-prone area and want to understand coverage. Share your home type and location.

## Your goal
Determine whether my specific home type (single-family wood-frame house) and location (California) are covered under a standard earthquake insurance policy, and what deductibles apply.

## Constraints on your behavior
['Initially only state that you live in an earthquake-prone area and want to understand coverage.', 'When asked, reveal your home type is a single-family wood-frame house and location is California.', 'Press for specifics about deductibles (e.g., percentage vs. fixed amount) and whether separate policies are needed.', "Mention that you've heard earthquakes aren't covered by standard homeowners insurance."]

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when you receive a clear answer about coverage for your home type and location, including the typical deductible percentage and whether a separate policy is required, OR after 5 chatbot turns.

## Success judgment
The chatbot is successful if it explicitly states that a standard homeowners policy does not cover earthquake damage, that a separate earthquake policy is needed, that a single-family wood-frame house in California is eligible, and provides a typical deductible range (e.g., 10-20% of dwelling coverage).
