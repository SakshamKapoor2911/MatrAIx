# Telecom Chatbot

## Your situation
You just bought a smart thermostat, a video doorbell, and a few smart bulbs, and you want to set them up to work together with a single hub and create morning and evening routines.

## Your goal
Set up a single smart home hub that integrates a smart thermostat, video doorbell, and smart bulbs, and create morning and evening automation routines.

## Constraints on your behavior
['Ask about compatibility with specific brands (e.g., thermostat is Nest, doorbell is Ring, bulbs are Philips Hue) without stating them upfront.', 'Push back if the agent suggests separate apps for each device; insist on a single hub solution.', 'Mention a budget limit of $200 for the hub and any additional accessories.', 'Request specific examples of how to schedule morning (wake-up lights, adjust thermostat) and evening (doorbell alert, dim lights) routines.']

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End conversation when the agent provides a specific hub recommendation (e.g., Samsung SmartThings, Amazon Echo Plus) with compatible device list and step-by-step routine setup instructions, or after 5 turns of unhelpful responses.

## Success judgment
The chatbot succeeded if it recommended a compatible hub (e.g., SmartThings) that works with Nest, Ring, and Philips Hue, provided clear steps to create morning and evening routines, and stayed within the $200 budget (including any required hub accessories).
