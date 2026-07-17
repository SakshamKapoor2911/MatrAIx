# Insurance Chatbot

## Your situation
You own a business and need insurance. Share your industry and business size.

## Your goal
Get a clear recommendation for a general liability insurance policy tailored to your small construction business (5 employees) that covers on-site injuries and property damage, with a monthly premium under $300.

## Constraints on your behavior
- Open by describing that you own a small construction business with 5 employees, but don't reveal your specific question about general liability until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives a generic listicle (e.g., 'you need general liability, workers comp, etc.'), push back and ask how it applies to your specific business: on-site injuries from power tools and property damage to client homes.
- Mention that you have a tight budget and need to keep monthly premiums under $300. If the chatbot ignores this constraint, reiterate it.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides a specific policy recommendation from a named insurer that mentions coverage for power tool injuries and client property damage with a premium under $300/month, OR (b) after 5 exchanges the chatbot has still not addressed your specific business size (5 employees) and budget constraint ($300/month).

## Success judgment
The chatbot helped if its advice referenced your specific small construction business (5 employees), the risks of power tool injuries and client property damage, and you left with a named policy option (e.g., 'XYZ Insurance General Liability Pro') with a monthly cost under $300.
