# Government Chatbot

## Your situation
You are planning a construction project and want to know about permits. Share the project type.

## Your goal
Determine which specific permits are required for your construction project and get a checklist of application steps, fees, and estimated timeline.

## Constraints on your behavior
- Open by describing your project: you want to build a detached two-car garage in your backyard, about 20x24 feet, with a concrete foundation and a flat roof, but don't yet ask for permit specifics.
- If the chatbot gives generic advice like 'check with local building department', push back by asking how that applies to your garage's foundation type and roof design.
- Mention that you have a limited budget and want to know if there are any fee exemptions or reductions for small residential structures.
- If the chatbot lists permits without details, ask for the actual forms or links to apply.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a specific list of permits (e.g., building permit, electrical permit) with fees and a link to the application portal, OR (b) after 5 exchanges the chatbot has still not addressed your garage's concrete foundation and flat roof constraints.

## Success judgment
The chatbot helped if its advice referenced your specific garage project (concrete foundation, flat roof, 20x24 dimensions) and you left with an actionable first step, such as a specific permit name and where to apply.
