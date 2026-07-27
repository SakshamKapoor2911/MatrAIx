# Automotive Chatbot

## Your situation
Your auto insurance is renewing and you want to review options. Share your current coverage and premium.

## Your goal
Compare my current auto insurance coverage (100/300/100 liability, $500 deductible, full coverage) and premium ($1,200/year) with at least two alternative quotes from different insurers to see if I can save money while maintaining similar coverage.

## Constraints on your behavior
['- Initially provide only basic info: state (California), vehicle (2020 Honda Civic), and current premium without details.', '- If the chatbot asks for more details, share current coverage (100/300/100 liability, $500 deductible, full coverage) and premium ($1,200/year).', '- Push back if the chatbot suggests reducing coverage or increasing deductible without explaining trade-offs.', '- Mention that I have a clean driving record (no accidents or tickets in 5 years) only if the chatbot asks about factors affecting premium.']

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total): share basic info, respond to requests for details, discuss at least two alternative quotes.

## Termination criteria
End the conversation when I have received at least two concrete quotes from different insurers (with coverage details and premiums) and can compare them to my current policy, OR after 8 messages have been exchanged without getting actionable quotes.

## Success judgment
The chatbot succeeded if it provided at least two specific quotes from different insurers (e.g., Geico: $1,050/year with same coverage; State Farm: $1,150/year with same coverage) and explained the differences in coverage or discounts. It failed if it only gave generic advice, did not ask for enough details to generate quotes, or pressured me to change coverage without clear justification.
