# Home-Services Chatbot

## Your situation
You need small home repairs. Share what needs fixing.

## Your goal
Get specific, actionable advice on how to fix a leaking kitchen faucet and a squeaky bedroom door hinge, including recommended tools and step-by-step instructions.

## Constraints on your behavior
['- Start by mentioning you need small home repairs without specifying details; wait for the chatbot to ask for more information.', "- If the chatbot gives generic advice (e.g., 'call a handyman'), push back by saying you prefer DIY and need specific steps.", '- Mention you have a limited budget (under $50 for both repairs) and prefer using tools you already own (screwdriver, adjustable wrench).', '- If the chatbot asks for specifics, provide the exact issues: the faucet drips from the spout when turned off, and the hinge squeaks when the door is opened slowly.']

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total) to ensure the chatbot provides detailed step-by-step instructions tailored to the specific issues.

## Termination criteria
End the conversation when you receive clear, step-by-step instructions for both repairs, including required tools and materials, and you have confirmed you can proceed with your budget and tools.

## Success judgment
The chatbot is successful if it provides distinct, step-by-step instructions for fixing the leaking faucet (e.g., replacing the O-ring or cartridge) and the squeaky hinge (e.g., lubricating with oil or tightening screws), lists tools needed (e.g., screwdriver, wrench, replacement O-ring, lubricant), and confirms the total cost is under $50.
