# Photography Chatbot

## Your situation
You have a GoPro Hero 11 and want to record smooth action footage of mountain biking trails, but the footage is shaky.

## Your goal
Get specific camera settings (e.g., HyperSmooth level, frame rate, field of view) and mounting advice (e.g., chest mount vs handlebar mount) to reduce shakiness in mountain biking footage.

## Constraints on your behavior
- Withhold that you are using a GoPro Hero 11 until asked.
- Push back if the chatbot suggests generic stabilizers or post-processing without first addressing camera settings.
- Mention that you are recording on rough mountain biking trails and need settings that work for fast, bumpy terrain.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End the conversation when you receive specific settings (e.g., HyperSmooth Boost, 1080p 60fps, Wide FOV) and mounting advice (e.g., chest mount) or after 5 turns have passed.

## Success judgment
The chatbot is successful if it recommends: (1) enabling HyperSmooth on Boost or High level, (2) using a frame rate of at least 60fps, (3) choosing a field of view like Wide or SuperView, and (4) mounting the camera on a chest harness or helmet. If it only suggests generic tripods or software stabilization, it fails.
