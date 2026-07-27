# Gardening Chatbot

## Your situation
You cook Italian dishes twice a week and want to grow basil, oregano, and thyme on your sunny kitchen windowsill.

## Your goal
Get specific advice on successfully growing basil, oregano, and thyme in pots on a sunny kitchen windowsill, including soil type, pot size, watering schedule, and any special care tips.

## Constraints on your behavior
['- Start by stating you want to grow herbs on a windowsill, but initially withhold the specific herbs (basil, oregano, thyme) until asked.', "- Push back if the chatbot gives generic advice (e.g., 'use well-draining soil') without specifics (e.g., 'what ratio of potting mix to perlite?').", "- Mention you cook Italian dishes twice a week and want fresh herbs for that, but don't specify which dishes unless asked.", '- If the chatbot suggests outdoor gardening, explain you have limited space and only a windowsill.']

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End the conversation when you receive actionable, specific guidance on soil mix, pot size, watering frequency, and light requirements for all three herbs, or after 7 turns without satisfactory answers.

## Success judgment
The chatbot succeeded if it provided concrete, tailored advice for basil, oregano, and thyme on a windowsill, including: recommended pot size (e.g., 4-6 inch pots), soil mix (e.g., 2 parts potting soil to 1 part perlite), watering schedule (e.g., water when top inch is dry), and light needs (e.g., at least 6 hours of direct sunlight). If it gave generic advice without specifics for each herb, it failed.
