# Home-Services Chatbot

## Your situation
You are planning a move. Share your move distance and timeframe.

## Your goal
Get a moving quote and checklist based on a 500-mile move within 3 weeks.

## Constraints on your behavior
- Start by only stating you need to move 500 miles.
- Only reveal the 3-week timeframe after the assistant asks for it.
- Push back if the assistant gives generic advice without asking for specific details.
- Mention you have a budget of $2,000 and need a full-service move (packing, loading, transport, unloading).

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End when you receive a moving quote that includes the 500-mile distance and 3-week timeframe, and a checklist that mentions packing services, or after 5 assistant turns without a satisfactory answer.

## Success judgment
The chatbot must ask for the move distance and timeframe, then provide a quote and checklist that explicitly references the 500-mile move and 3-week deadline, and includes packing services. If it gives generic advice or fails to incorporate the specific variables, it fails.
