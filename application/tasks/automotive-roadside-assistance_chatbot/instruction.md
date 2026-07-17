# Automotive Chatbot

## Your situation
You have a roadside emergency. The chatbot guides you through your options.

## Your goal
Get step-by-step instructions for safely changing a flat tire on the side of a busy highway, including where to position the spare and how to use the jack.

## Constraints on your behavior
- Open by describing your situation: you're on the shoulder of I-95, it's raining, and you have a flat tire on the driver's side rear. Don't ask for instructions yet; wait for the chatbot to ask or give generic advice.
- If the chatbot gives generic advice like 'call for roadside assistance,' push back and explain that you have a spare tire and jack but have never changed a tire before, especially in the rain.
- Mention that you're worried about safety because cars are passing close and you have your child in the back seat. Ask if you should try to change it yourself or wait for help.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) the chatbot provides specific instructions for safely jacking up the car on the shoulder and changing the tire, including where to place the jack and how to stay visible, OR (b) after 5 exchanges the chatbot has still not addressed your specific concerns about rain, traffic, and the child in the car.

## Success judgment
The chatbot helped if it gave concrete, safety-oriented steps for changing the tire on the highway in the rain, such as using hazard lights, placing flares, positioning the jack on the frame, and keeping the child inside the car, and you felt confident to proceed or decided to call for help based on its advice.
