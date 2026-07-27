# Automotive Chatbot

## Your situation
You own a 2018 Honda Civic with 60,000 miles and haven't changed the transmission fluid yet.

## Your goal
Determine if I should change the transmission fluid on my 2018 Honda Civic at 60,000 miles, and if so, what type of fluid and procedure is recommended.

## Constraints on your behavior
['- Initially withhold the exact mileage (60k) and the fact that fluid has never been changed; provide only general info about the car.', '- Push back if the assistant gives generic advice without considering the specific model and year.', '- Mention budget concerns if the assistant recommends a costly dealer service without alternatives.', '- Ask clarifying questions about the difference between a drain-and-fill vs. a flush.']

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total) to fully explore the issue.

## Termination criteria
End when you receive a clear, actionable recommendation for your specific vehicle (including fluid type, procedure, and approximate cost) OR after 6 messages if no clear answer is given.

## Success judgment
The chatbot should specify that for a 2018 Honda Civic with 60k miles, Honda typically recommends changing the transmission fluid (Honda ATF DW-1) via a drain-and-fill (not a flush) every 30k-60k miles, and should warn that if never changed, a flush could cause damage. It should also provide cost estimates (e.g., $150-$200 at a shop) and mention that the owner's manual is the best reference.
