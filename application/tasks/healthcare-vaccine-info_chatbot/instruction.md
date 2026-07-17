# Healthcare Chatbot

## Your situation
You have questions about vaccinations. Share which vaccine or what concerns you.

## Your goal
Determine whether you need a specific vaccine (e.g., shingles vaccine) given your age (55) and a mild egg allergy, and get a clear recommendation on timing and any precautions.

## Constraints on your behavior
- Open by describing your situation: you're 55, have a mild egg allergy, and are considering the shingles vaccine, but don't state your exact question until the chatbot asks a follow-up or gives generic advice.
- If the chatbot gives generic advice (e.g., 'talk to your doctor'), push back and ask how it applies to your specific egg allergy and the shingles vaccine.
- Mention that you've heard conflicting information about egg allergies and vaccines, and want clarification on whether the shingles vaccine (which is not egg-based) is safe for you.
- Budget is not a concern, but you want to avoid unnecessary appointments or extra costs.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you receive a clear recommendation that references your egg allergy and the shingles vaccine (e.g., 'the shingles vaccine is safe for people with egg allergies, you can get it at your pharmacy'), OR (b) after 5 exchanges the chatbot has still not addressed your specific egg allergy or the shingles vaccine.

## Success judgment
The chatbot helped if its advice referenced your specific egg allergy and shingles vaccine (not generic tips) and you left knowing whether you should get the vaccine and any steps to take (e.g., no special precautions needed, or you should consult an allergist first).
