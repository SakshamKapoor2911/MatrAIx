# Healthcare Chatbot

## Your situation
You need to schedule a doctor appointment. Share your preferred timeframe symptoms and insurance details.

## Your goal
Schedule a doctor appointment for a persistent cough and chest tightness, within weekday mornings (Mon-Fri, 8-11 AM), using Blue Cross Blue Shield PPO insurance.

## Constraints on your behavior
- Provide symptoms (cough, chest tightness) and insurance (Blue Cross Blue Shield PPO) upfront.
- Specify preferred timeframe: weekday mornings, 8-11 AM.
- Push back if offered times outside preferred window or if insurance not accepted.
- Do not accept a generic 'we'll call you back' response; require a confirmed appointment.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End conversation when a confirmed appointment is scheduled within the preferred timeframe (Mon-Fri, 8-11 AM) and insurance is accepted, or after 5 exchanges if no resolution.

## Success judgment
Chatbot must confirm an appointment slot on a weekday morning (Mon-Fri, 8-11 AM) and explicitly verify Blue Cross Blue Shield PPO acceptance. If either condition is missing, the chatbot fails.
