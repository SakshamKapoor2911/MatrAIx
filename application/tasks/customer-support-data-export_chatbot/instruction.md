# Customer-Support Chatbot

## Your situation
You're leaving an online service and need to download your account history, including past orders and personal information, before the account is closed. You want the data in a CSV format.

## Your goal
Download account history including past orders and personal information in CSV format before account closure.

## Constraints on your behavior
- Initially request only general data export without specifying format.
- When offered PDF or other formats, explicitly request CSV.
- If asked for specific data fields, list: order dates, item names, prices, shipping addresses, and account email.
- Mention urgency: account closure deadline is in 3 days.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total).

## Termination criteria
End when CSV export link is provided and confirmed to include all requested fields, or after 5 chatbot responses without resolution.

## Success judgment
Chatbot provided a downloadable CSV file containing order dates, item names, prices, shipping addresses, and account email, and confirmed the data is exportable before account closure deadline.
