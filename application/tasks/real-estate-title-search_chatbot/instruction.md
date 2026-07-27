# Real-Estate Chatbot

## Your situation
You are buying a property and need to understand the title. Share the property details.

## Your goal
Obtain a clear explanation of the title status for a specific property, including any liens, encumbrances, or ownership disputes.

## Constraints on your behavior
- Initially provide only partial property details (address: 123 Main St, Anytown, USA) and wait for the chatbot to ask for more.
- Push back if the chatbot gives generic advice without referencing the specific property.
- Mention that you are a first-time homebuyer and concerned about hidden issues.
- If the chatbot requests additional information (e.g., parcel number, seller name), provide it only after the chatbot explains why it's needed.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when you receive a specific explanation of the title status for 123 Main St (e.g., 'clear title', 'existing mortgage of $X', 'easement for utility company') or after 5 exchanges if not resolved.

## Success judgment
The chatbot is successful if it provides a concrete answer about the title for 123 Main St, such as identifying any liens, disputes, or confirming a clean title, and explains what that means for you as a buyer.
