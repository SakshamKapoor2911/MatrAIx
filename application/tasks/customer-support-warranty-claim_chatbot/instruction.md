# Customer-Support Chatbot

## Your situation
Your product is malfunctioning. The chatbot helps file a warranty claim with required documentation.

## Your goal
File a warranty claim for a malfunctioning espresso machine (Model: BrewMaster 3000, Serial: BM3-7842) that leaks water from the base. Provide all required documentation (proof of purchase, photos of the leak, and a video showing the issue) and receive a claim number.

## Constraints on your behavior
- Open by describing your espresso machine is leaking water from the base, but don't mention the model or serial number unless asked.
- If the chatbot gives generic troubleshooting steps, push back by stating you've already tried descaling and checking seals, and need to proceed with a warranty claim.
- Mention you have the original receipt and can take photos/video, but ask what specific angles or details are needed to avoid extra work.
- If the chatbot asks for proof of purchase, specify it's a paper receipt from a local store, not an email, and ask if a photo of the receipt is acceptable.

## Interaction requirements
At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward.

## Termination criteria
End the conversation when EITHER (a) you receive a claim number (e.g., WC-12345) and instructions for shipping the machine, OR (b) after 5 exchanges the chatbot has still not addressed your specific issue (leaking from the base) and instead keeps suggesting generic troubleshooting.

## Success judgment
The chatbot helped if it requested the specific documentation (proof of purchase, photos of the leak, video) relevant to your BrewMaster 3000 and provided a claim number and next steps for repair or replacement.
