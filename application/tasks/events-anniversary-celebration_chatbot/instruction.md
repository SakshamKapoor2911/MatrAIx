# Events Chatbot

## Your situation
Your 10th wedding anniversary is coming up and you want to plan a romantic weekend getaway with a budget of $1,500, including a special gift.

## Your goal
Plan a romantic weekend getaway for my 10th wedding anniversary within a $1,500 budget, including a special gift.

## Constraints on your behavior
- Start by stating the anniversary and desire for a romantic getaway.
- Initially withhold the budget; only reveal if asked.
- Push back on suggestions exceeding $1,500 total.
- Emphasize the need for a special gift within the budget.

## Interaction requirements
At least three back-and-forth exchanges (6+ messages total).

## Termination criteria
End when a complete itinerary is provided with total cost under $1,500 and includes a gift suggestion, or after 5 user turns.

## Success judgment
The chatbot must suggest a weekend destination, accommodations, activities, and a specific gift (e.g., jewelry, personalized item) with total cost ≤ $1,500. If any part is missing or over budget, it fails.
