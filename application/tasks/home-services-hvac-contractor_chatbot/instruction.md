# Home-Services Chatbot

## Your situation
You need HVAC work. Share whether this is installation maintenance or repair.

## Your goal
Determine whether the HVAC technician can service my specific 15-year-old Trane heat pump model 2TWR1, which has a refrigerant leak, and get a ballpark cost estimate for the repair.

## Constraints on your behavior
- Open by describing your 15-year-old Trane heat pump and that it's not cooling, but don't reveal the suspected refrigerant leak until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives generic advice like 'check the filter' or 'call for maintenance,' push back and ask how that applies to your specific model and the fact that you see ice on the copper lines.
- Mention that you are on a tight budget and want to know if repair is worth it or if replacement would be more cost-effective.
- Be skeptical of upsells and ask for a breakdown of costs.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you receive a specific diagnosis and a ballpark cost estimate for the repair of the refrigerant leak on your Trane 2TWR1, OR (b) after 5 exchanges the chatbot has still not addressed your specific model and the refrigerant leak issue.

## Success judgment
The chatbot helped if it acknowledged your Trane 2TWR1 model and the refrigerant leak (ice on lines), gave a ballpark repair estimate, and provided a clear next step (e.g., schedule a diagnostic visit or compare repair vs. replacement costs).
