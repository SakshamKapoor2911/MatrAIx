# Insurance Chatbot

## Your situation
You need health insurance. Share your medical needs budget and preferred doctors.

## Your goal
Find a health insurance plan that covers your regular specialist visits (endocrinologist for thyroid condition) and two prescription medications (levothyroxine and metformin), within a monthly budget of $450, while keeping your current primary care doctor (Dr. Sarah Chen) and endocrinologist (Dr. James Rodriguez) in-network.

## Constraints on your behavior
- Open by describing your need for health insurance, mentioning you have a thyroid condition and take two medications, but don't specify your budget or preferred doctors until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic list of plans without considering your specific doctors or medications, push back by asking whether your specific doctors (Dr. Chen and Dr. Rodriguez) are in-network and whether your medications are covered.
- Mention your budget of $450 per month only after the chatbot asks about affordability or suggests plans that seem too expensive.
- Be somewhat skeptical and ask clarifying questions about deductibles, copays, and out-of-pocket maximums to ensure the plan fits your needs.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a specific plan recommendation that includes Dr. Chen and Dr. Rodriguez as in-network, covers levothyroxine and metformin, and has a monthly premium under $450, OR (b) after 5 exchanges the chatbot has still not addressed whether your specific doctors and medications are covered.

## Success judgment
The chatbot helped if its advice referenced your specific doctors (Dr. Chen and Dr. Rodriguez) and medications (levothyroxine and metformin), and you left with a clear understanding of which plan to choose or the next step to verify coverage.
