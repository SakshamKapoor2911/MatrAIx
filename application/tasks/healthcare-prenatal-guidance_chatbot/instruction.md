# Healthcare Chatbot

## Your situation
You are pregnant or planning to become pregnant. Share your stage and any questions about prenatal care.

## Your goal
Get personalized advice on prenatal nutrition, specifically which supplements to prioritize and which foods to emphasize, given your stage of pregnancy.

## Constraints on your behavior
- Open by describing your situation: you are 12 weeks pregnant with mild nausea and fatigue, and you have a history of anemia. Don't reveal your specific question about supplements until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives generic advice like 'eat a balanced diet', push back and ask how it applies to your specific history of anemia and the fact that you are vegetarian.
- Mention that you are on a tight budget and cannot afford expensive supplements.
- Only ask about specific supplements (like iron vs. folate vs. DHA) after the chatbot addresses your anemia.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot recommends a specific supplement brand and dosage that accounts for your anemia and vegetarianism, OR (b) after 5 exchanges the chatbot has still not addressed your specific history of anemia or vegetarian diet.

## Success judgment
The chatbot helped if its advice referenced your specific history of anemia and vegetarian diet (not generic tips) and you left with an actionable first step you could take, such as a specific supplement to buy or a food list tailored to your needs.
