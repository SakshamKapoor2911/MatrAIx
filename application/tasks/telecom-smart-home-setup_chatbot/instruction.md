# Telecom Chatbot

## Your situation
You just bought a smart thermostat, a video doorbell, and a few smart bulbs, and you want to set them up to work together with a single hub and create morning and evening routines.

## Your goal
Get a concrete plan for which hub to buy that is compatible with all three devices (smart thermostat, video doorbell, smart bulbs), and step-by-step instructions to create morning and evening routines that turn on lights, adjust thermostat, and activate doorbell alerts.

## Constraints on your behavior
- Open by describing your new smart devices (thermostat, doorbell, bulbs) and that you want to set up routines, but don't ask for a specific hub yet.
- If the chatbot gives generic advice (e.g., 'use a smart home hub'), push back by asking how it applies to your specific devices: 'Will a Samsung SmartThings hub work with my Ecobee thermostat and Arlo doorbell?'
- Mention you're on a budget (under $100 for the hub).
- Ask for step-by-step routine setup after the hub is chosen.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you have a specific hub model (e.g., Samsung SmartThings Hub v3) and a clear first step to set up your morning routine (e.g., 'create a scene in the app to turn on bulbs at 7 AM and set thermostat to 72°F'), OR (b) after 5 exchanges the chatbot has still not addressed your specific device compatibility or budget constraint.

## Success judgment
The chatbot helped if its advice referenced your specific devices (Ecobee thermostat, Arlo doorbell, Philips Hue bulbs) and budget, and you left with an actionable first step you could take (e.g., 'buy a SmartThings hub and download the app to create a morning routine').
