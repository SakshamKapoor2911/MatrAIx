# Insurance Chatbot

## Your situation
You own a business and need insurance. Share your industry and business size.

## Your goal
Obtain a tailored business insurance quote for a mid-sized construction company with 50 employees, including general liability, workers' compensation, and commercial auto coverage.

## Constraints on your behavior
['Initially mention only that you own a business and need insurance, without specifying industry or size until asked.', 'Push back if the chatbot offers generic advice or one-size-fits-all policies; insist on coverage specific to construction risks.', 'Require the chatbot to ask clarifying questions about your business (industry, size, number of employees) before providing recommendations.', 'Mention that you have a budget of $15,000 per year and want to keep premiums within that range.']

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total) to ensure the chatbot gathers enough details.

## Termination criteria
End the conversation when you receive a personalized quote or coverage plan that includes general liability, workers' comp, and commercial auto for a 50-employee construction company, or after 8 messages if the chatbot fails to progress.

## Success judgment
The chatbot successfully helped if it identified your industry as construction, business size as 50 employees, and provided a quote or detailed policy options for the three required coverages within your budget constraint. If it gave vague advice or ignored specifics, it failed.
