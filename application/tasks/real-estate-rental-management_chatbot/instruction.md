# Real-Estate Chatbot

## Your situation
You own or manage a rental property. Share your questions about tenants maintenance or legal requirements.

## Your goal
Get clear guidance on how to handle a tenant's request for urgent plumbing repairs, including legal obligations and recommended timeline, specifically for a property in Oregon.

## Constraints on your behavior
["- Start by describing the issue generally (e.g., 'a tenant reported a leaky pipe') without specifying urgency or location.", "- If the chatbot gives generic advice (e.g., 'fix it quickly'), push back by asking about legal requirements and potential liability.", '- Only reveal the property is in Oregon and the leak is causing water damage if the chatbot asks for more details or gives vague advice.', '- Act frustrated if the chatbot fails to mention local laws or specific repair timelines.']

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total) to ensure the chatbot gathers enough details to give specific advice.

## Termination criteria
End the conversation when the chatbot provides a clear answer referencing Oregon landlord-tenant law (e.g., repair timeline of 24-48 hours for emergencies) and actionable steps (e.g., document the request, provide written notice).

## Success judgment
The chatbot succeeded if it explicitly mentions Oregon's implied warranty of habitability, the 24-hour emergency repair requirement for plumbing, and advises the landlord to provide a written notice of repair timeline. Failure if it only gives generic advice or does not address legal liability.
