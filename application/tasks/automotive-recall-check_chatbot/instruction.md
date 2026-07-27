# Automotive Chatbot

## Your situation
You just bought a used 2020 Ford Explorer and want to check if there are any open recalls.

## Your goal
I want to find out if my 2020 Ford Explorer has any open recalls and get details on how to get them fixed.

## Constraints on your behavior
- Start by asking about recalls for a 2020 Ford Explorer without providing the VIN initially.
- If asked for the VIN, resist at first by saying you don't have it handy, then after one prompt, provide VIN: 1FM5K8D8XLGA12345.
- Ask for specifics: what the recall is about, severity, and what to do next.
- Mention you bought it used and want to ensure it's safe.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End when I receive a clear answer listing any open recalls for VIN 1FM5K8D8XLGA12345 and instructions on how to get them fixed, or after 5 turns without a satisfactory answer.

## Success judgment
The chatbot successfully retrieved recall information for VIN 1FM5K8D8XLGA12345 and provided actionable steps (e.g., contact dealer, schedule free repair). If the chatbot fails to ask for VIN or gives generic advice without specific recall details, it fails.
