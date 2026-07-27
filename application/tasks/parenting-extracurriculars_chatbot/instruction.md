# Parenting Chatbot

## Your situation
Your child wants to start activities. Share their age interests and schedule.

## Your goal
Get personalized activity recommendations for a 7-year-old child who is interested in soccer and art, with availability on weekday afternoons after 3pm and weekends.

## Constraints on your behavior
- Start by stating the child is 7 years old and wants to start activities, but initially only mention interest in 'sports and creative stuff' without specifying soccer and art until asked.
- Push back if the chatbot suggests activities that are too expensive (budget under $100/month total) or require early morning/evening times (only available after 3pm on weekdays and all day weekends).
- Ask for details about class size and safety if the chatbot suggests team sports or art classes.
- Mention that the child is shy and prefers small groups or one-on-one settings.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when the chatbot provides 2-3 specific activity options with details on schedule, cost, and class size that match the constraints (soccer/art, weekday afternoons/weekends, under $100/month, small group), or after 5 turns without satisfactory options.

## Success judgment
The chatbot successfully recommends at least one soccer program and one art class that are available on weekday afternoons or weekends, cost under $100/month total, and have small class sizes (e.g., 8-10 kids or less). It should also acknowledge the child's shyness and suggest a trial session or beginner class.
