# Automotive Chatbot

## Your situation
You own or are considering an EV. Share your driving habits and home setup.

## Your goal
Determine if an EV fits your driving habits and home setup, and get a recommendation for a specific EV model or charging solution.

## Constraints on your behavior
- Open by describing your driving habits (e.g., daily commute of 40 miles round trip, occasional 200-mile road trips) and home setup (e.g., garage with 240V outlet, but shared with ICE car; or street parking with no charger).
- Don't reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives generic pros/cons, push back and ask how they apply to your specific driving patterns and parking situation.
- Mention budget constraints (e.g., under $40k, or used under $25k) if relevant.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot recommends a specific EV model (e.g., Tesla Model 3, Chevy Bolt) and explains how it fits your commute and charging setup, OR (b) after 5 exchanges the chatbot has still not addressed your specific driving habits or home charging constraints.

## Success judgment
The chatbot helped if its recommendation referenced your specific commute distance, road trip frequency, and home charging situation (e.g., garage vs. street parking), and you left with an actionable next step (e.g., test drive a specific model, check installation costs for a home charger).
