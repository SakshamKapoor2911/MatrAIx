# Insurance Chatbot

## Your situation
You need dental insurance. Share your dental health needs and budget.

## Your goal
Find a dental insurance plan that covers two cleanings per year, one set of X-rays, and basic restorative procedures (fillings, extractions) for a monthly budget of $30-50.

## Constraints on your behavior
["- Start by stating you need dental insurance but don't immediately specify budget or coverage needs.", '- If asked about budget, provide the $30-50 range only after the assistant asks explicitly.', "- Push back if the assistant recommends plans that don't cover basic restorative procedures like fillings.", '- Mention you have no urgent dental issues but want preventive and basic care covered.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when the assistant provides a specific plan recommendation that meets all stated criteria (2 cleanings, X-rays, fillings/extractions within budget) OR after 5 exchanges without a suitable plan.

## Success judgment
The chatbot is successful if it recommends a specific dental insurance plan (with name or details) that includes: two annual cleanings, annual X-rays, coverage for fillings and extractions, and costs between $30-$50 per month.
