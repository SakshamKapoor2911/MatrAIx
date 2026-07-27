# Customer-Support Chatbot

## Your situation
You heard about a product recall and want to check if yours is affected.

## Your goal
Find out if my specific product (model number ABC-123, purchased in January 2023) is affected by the recall, and if so, what the next steps are (return/repair/replacement).

## Constraints on your behavior
- Start by stating you heard about a recall but don't immediately give the model number; wait for the chatbot to ask for details.
- If the chatbot asks for the model number, provide it (ABC-123) and purchase date (January 2023).
- If the chatbot gives generic advice without checking the specific model, push back and ask to verify against the recall list.
- If the chatbot confirms the model is affected, ask for specific instructions on what to do next.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when the chatbot has either confirmed that my product is not affected by the recall, or provided clear actionable steps (e.g., return label, repair appointment, replacement process).

## Success judgment
- The chatbot correctly identifies whether model ABC-123 is affected by the recall.
- If affected, the chatbot provides specific next steps (e.g., how to return, repair, or get a replacement) rather than just saying 'contact support'.
- The chatbot does not require multiple repetitions of the model number or purchase date.
