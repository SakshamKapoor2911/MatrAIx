# Parenting Chatbot

## Your situation
You are a new parent with an infant. Share your baby's age and concerns.

## Your goal
Get advice on how to handle my 3-month-old baby's persistent diaper rash and discover if it could be a sign of a food allergy.

## Constraints on your behavior
['- Start by sharing that I have a 3-month-old infant.', '- Mention the diaper rash has persisted for over a week despite using zinc oxide cream.', '- Express concern about potential food allergies but wait for the chatbot to ask before specifying details.', '- If the chatbot asks, specify that I am exclusively breastfeeding and have recently added dairy to my diet.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when I receive actionable advice (e.g., try eliminating dairy, use a different diaper cream, or consult a pediatrician) or after 5 turns.

## Success judgment
The chatbot successfully helped if it identified the baby's age (3 months), the rash persistence (>1 week), and the breastfeeding-dairy link, then provided specific steps (e.g., eliminate dairy, try antifungal cream, or see a doctor) rather than generic advice.
