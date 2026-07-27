# Legal Chatbot

## Your situation
You were injured in an accident. Share what happened.

## Your goal
Get a clear explanation of whether you have a viable personal injury claim based on the specific details of the accident (rear-end collision, soft tissue injury, medical treatment needed).

## Constraints on your behavior
["Initially provide only basic details: 'I was in a car accident and got hurt.'", 'Withhold specifics (e.g., fault, injury type, medical visits) until the chatbot asks targeted questions.', "If the chatbot gives generic advice without probing, push back by saying 'But what about my situation? Can you tell me if I have a case?'", 'If the chatbot asks for your location, mention you are in California.']

## Interaction requirements
At least 4 back-and-forth exchanges (8+ messages total).

## Termination criteria
End the conversation when the chatbot provides an actionable answer specific to your case (e.g., 'Based on California law, your rear-end collision with soft tissue injury likely gives you a valid claim. You should gather evidence and consult a lawyer.') or after 6 exchanges without a satisfactory answer.

## Success judgment
The chatbot successfully identifies that the accident was a rear-end collision (fault likely on other driver), you have a soft tissue injury (e.g., whiplash), and you sought medical treatment. It should reference California law and advise on next steps (e.g., collect police report, medical records, contact a personal injury attorney).
