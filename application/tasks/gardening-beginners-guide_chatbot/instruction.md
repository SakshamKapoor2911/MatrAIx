# Gardening Chatbot

## Your situation
You have a 10x10 foot sunny backyard patch that's currently just dirt and weeds, and you want to grow tomatoes and basil.

## Your goal
Get a step-by-step plan to prepare the 10x10 sunny patch and successfully plant tomatoes and basil, including soil amendment, planting schedule, and variety recommendations.

## Constraints on your behavior
- Start by describing the patch size and sunlight, but initially withhold that it's currently dirt and weeds; reveal only if asked.
- Push back if the chatbot gives overly generic advice (e.g., 'just plant them') by asking for specifics like 'What soil prep do I need for my patch?'
- Mention a budget constraint of $50 if the chatbot suggests expensive products.
- Ask clarifying questions if terms are unclear (e.g., 'What does 'amend soil' mean?').

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total) to ensure depth.

## Termination criteria
End the conversation when you receive a clear, actionable step-by-step plan that includes: soil testing/amendment, planting depth and spacing for both tomatoes and basil, and a timeline for planting in your climate zone (assume zone 7). Or if the chatbot fails to provide specifics after 5 exchanges.

## Success judgment
The chatbot is successful if it: (1) asks about or addresses the current state (dirt/weeds), (2) recommends specific soil amendments (e.g., compost, pH adjustment), (3) gives planting depth (tomatoes deep, basil shallow) and spacing (2-3 ft for tomatoes, 1 ft for basil), (4) provides a timeline (e.g., after last frost, succession planting for basil), and (5) stays within a $50 budget or offers low-cost alternatives.
