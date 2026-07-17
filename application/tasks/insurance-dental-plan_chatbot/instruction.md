# Insurance Chatbot

## Your situation
You need dental insurance. Share your dental health needs and budget.

## Your goal
Find a dental insurance plan that covers at least two cleanings per year, basic fillings, and a root canal, with a monthly premium under $50 and an annual deductible under $500.

## Constraints on your behavior
- Open by describing your dental health needs (e.g., need regular cleanings, have a cracked molar that may need root canal, and want coverage for fillings), but don't reveal your specific budget or deductible limit until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic list of plans without addressing your cracked molar or budget constraints, push back and ask how each plan applies to your specific situation, especially the root canal coverage.
- Mention that you're on a tight budget and need to keep monthly costs low, but don't specify the exact premium or deductible limits until prompted.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot recommends a specific plan that covers root canals with a premium under $50 and deductible under $500, OR (b) after 5 exchanges the chatbot has still not addressed your cracked molar and budget constraints.

## Success judgment
The chatbot helped if its advice referenced your specific cracked molar and budget (premium under $50, deductible under $500) and you left with a concrete plan name or quote to apply for.
