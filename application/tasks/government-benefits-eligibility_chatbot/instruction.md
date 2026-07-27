# Government Chatbot

## Your situation
You're a single parent with two kids earning $35,000/year. You want to know if you qualify for SNAP or Medicaid.

## Your goal
Find out if I qualify for SNAP or Medicaid based on my income of $35,000/year and household size of 3 (single parent with two kids).

## Constraints on your behavior
['Provide accurate household size and income only when asked directly.', 'If the chatbot gives generic info, ask for specific income thresholds for a family of 3.', 'Mention that you are a single parent and have two children, but do not volunteer specific ages unless asked.', "If the chatbot asks for state, provide 'Texas' (or any default state) to test location-specific eligibility."]

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when the chatbot gives a clear yes/no answer regarding SNAP and Medicaid eligibility for your specific income and household size, or after 5 chatbot messages if unclear.

## Success judgment
The chatbot successfully determines that a household of 3 with $35,000/year likely exceeds SNAP income limits (typically 130% FPL) but may qualify for Medicaid if children are covered under CHIP. The chatbot should provide state-specific thresholds or direct to application.
