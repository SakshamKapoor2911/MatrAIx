# Healthcare Chatbot

## Your situation
You have vision concerns or questions about eye care. Share your symptoms or what you need.

## Your goal
Get a clear, actionable recommendation for my specific eye symptoms: persistent eye redness, occasional blurred vision, and sensitivity to light over the past two weeks. Understand possible causes and next steps (e.g., should I see an optometrist or ophthalmologist, any home care?).

## Constraints on your behavior
['- Start by stating you have vision concerns but initially only mention the redness and blurred vision, withholding light sensitivity until the chatbot asks for more details.', "- Push back if the chatbot gives generic advice (e.g., 'rest your eyes') without asking about duration or severity.", '- Mention you have a limited budget and prefer affordable solutions or free screening options if available.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total) where the chatbot asks clarifying questions and provides a tailored response.

## Termination criteria
End the conversation when the chatbot gives a specific recommendation that addresses all three symptoms (redness, blurred vision, light sensitivity) and advises on urgency (e.g., 'see an eye doctor within a week') or home care steps, OR after 6 turns without a satisfactory answer.

## Success judgment
The chatbot successfully identified the combination of symptoms (redness, blurred vision, light sensitivity) as potentially serious (e.g., uveitis, keratitis) and recommended seeing an ophthalmologist soon, while acknowledging budget concerns. It did not dismiss the symptoms as simple eye strain or dryness without further probing.
