# Automotive Chatbot

## Your situation
You are in the market for a car. Share your budget and preferences.

## Your goal
Get a specific car recommendation (make, model, and year) that fits my $25,000 budget, needs all-wheel drive, and has good fuel economy (at least 30 mpg highway).

## Constraints on your behavior
- Open by describing your situation: 'I'm looking for a car with a $25,000 budget, need all-wheel drive, and want good fuel economy.' But don't reveal your specific question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle (e.g., 'here are some popular AWD cars'), push back and ask how it applies to your specific needs: 'Can you narrow that down to something under $25k and over 30 mpg highway?'
- Mention that you plan to keep the car for at least 5 years and need something reliable.
- If the chatbot suggests a car, ask about cargo space or safety ratings if not provided.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot recommends a specific car (make, model, year) that meets your budget of $25,000, AWD, and 30 mpg highway, OR (b) after 5 exchanges the chatbot has still not addressed your specific budget and fuel economy constraints.

## Success judgment
The chatbot helped if its recommendation included a specific make, model, and year that fits your $25,000 budget, has AWD, and achieves at least 30 mpg highway, and you felt confident to test drive it.
