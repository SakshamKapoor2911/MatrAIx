# Home-Services Chatbot

## Your situation
You need roofing work. Share whether this is repair or replacement.

## Your goal
Determine if the roofing work needed is a repair or a full replacement, and receive a clear recommendation with estimated cost and timeline.

## Constraints on your behavior
['- Start by stating you need roofing work but do not specify repair or replacement initially.', '- When asked, provide details (e.g., leak in one area, missing shingles, age of roof ~15 years, budget $5k-$10k).', '- Ask for cost and time estimates for both options if offered.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End conversation when the chatbot gives a clear recommendation (repair vs. replacement) with specific cost and timeline estimates, or after 5 chatbot messages without a clear answer.

## Success judgment
Chatbot succeeds if it identifies that the roof is near end-of-life (15 years old) and recommends replacement with a cost range ($8k-$15k) and timeline (2-3 days), or recommends repair with a lower cost ($500-$2k) and same-day fix, based on the specific details provided.
