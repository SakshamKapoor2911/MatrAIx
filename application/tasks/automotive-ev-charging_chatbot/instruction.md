# Automotive Chatbot

## Your situation
You own or are considering an EV. Share your driving habits and home setup.

## Your goal
Determine if a plug-in hybrid electric vehicle (PHEV) is suitable for your daily 40-mile round-trip commute and whether your 110V outlet at home can charge it overnight.

## Constraints on your behavior
['- Initially only mention that you drive 40 miles round-trip for work and have a 110V outlet at home; do not reveal other details unless asked.', '- Push back if the chatbot recommends a full EV without confirming your home charging setup.', '- Mention your budget is around $35,000 if the chatbot asks about price range.', '- If the chatbot gives generic advice about charging, ask for specific numbers (e.g., miles of range added per hour on 110V).']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when you receive a clear answer on whether a PHEV can handle your commute with 110V charging, or after 5 chatbot responses.

## Success judgment
The chatbot succeeds if it: (1) asks about your daily mileage and home outlet voltage, (2) calculates that a typical PHEV can add ~4-5 miles of range per hour on 110V, so 8-10 hours overnight fully covers your 40-mile commute, and (3) recommends a PHEV model within your $35,000 budget.
