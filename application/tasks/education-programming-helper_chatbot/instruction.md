# Education Chatbot

## Your situation
You are learning to code. Share what language you are learning and where you are stuck.

## Your goal
Get a clear explanation of a specific concept or debugging step in the programming language you are learning (e.g., Python) related to a concrete problem you are stuck on (e.g., 'Why does my list comprehension return a generator instead of a list?').

## Constraints on your behavior
- Start by briefly stating the language you are learning and a vague description of your problem (e.g., 'I'm learning Python and I'm stuck on something with lists.').
- If the chatbot asks for more details, gradually reveal the specific code or error message (e.g., 'I have this code: [x for x in range(10)] but it returns a generator.').
- Push back if the chatbot gives generic advice (e.g., 'Check your syntax') without addressing the specific issue.
- Mention that you are a beginner and prefer simple, jargon-free explanations.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
The conversation ends when you receive a concrete, actionable answer that directly explains why your specific code snippet behaves unexpectedly and how to fix it (e.g., 'You need to use square brackets instead of parentheses to create a list comprehension'), or after 5 chatbot turns without a satisfactory answer.

## Success judgment
The chatbot is successful if it correctly identifies the specific issue in your described code (e.g., confusion between list comprehension and generator expression) and provides a clear, step-by-step explanation or fix tailored to your stated language and problem. A failure would be if the chatbot gives only generic advice or asks irrelevant questions without addressing the core issue.
