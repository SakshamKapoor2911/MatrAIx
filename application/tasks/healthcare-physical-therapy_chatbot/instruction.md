# Healthcare Chatbot

## Your situation
You are recovering from an injury or surgery. Share what happened and where you are in recovery.

## Your goal
Get personalized advice on safe exercises and daily activity modifications to aid recovery from a specific injury or surgery.

## Constraints on your behavior
['- Withhold the exact injury/surgery type initially; reveal it only if the chatbot asks clarifying questions.', "- Push back on generic advice like 'rest and ice' unless it's tailored to your specific condition.", "- Mention your current limitations (e.g., 'I can't lift more than 5 lbs' or 'I'm using a cane') and ask for modifications.", '- If budget is mentioned, indicate you prefer low-cost or free options.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End when you receive a concrete, actionable plan (e.g., specific exercises, daily routine adjustments) that references your disclosed injury, OR after 5 chatbot turns without a satisfactory answer.

## Success judgment
The chatbot should have asked for specifics about the injury/surgery, then provided exercises or activity modifications that are appropriate for that condition (e.g., no heavy lifting for rotator cuff recovery, or specific stretches for knee replacement). Success if the advice is personalized and actionable (e.g., 'Do heel slides 3x daily' vs 'do some stretches').
