#!/usr/bin/env bash
set -euo pipefail

# Reference solution for the chat_meal-planning-nutrition task.
# This script simulates a persona conversation with the meal-plan-api sidecar.

API_BASE="${CHATBOT_API_URL:-http://meal-plan-api:8000}"
OUTPUT_DIR="${PERSONABENCH_OUTPUT_DIR:-${MATRIX_OUTPUT_DIR:-/app/output}}"
mkdir -p "${OUTPUT_DIR}"

# Create a session
echo "Creating session..."
SESSION_RESPONSE=$(curl -s -X POST "${API_BASE}/v1/session" \
  -H "Content-Type: application/json" \
  -d '{"domain": "meal_planning"}')
SESSION_ID=$(echo "${SESSION_RESPONSE}" | python3 -c "import json,sys; print(json.load(sys.stdin)['sessionId'])")
echo "Session: ${SESSION_ID}"

# Send messages (simulating a persona conversation)
echo "--- Turn 1: Initial greeting ---"
M1=$(curl -s -X POST "${API_BASE}/v1/messages" \
  -H "Content-Type: application/json" \
  -d "{\"sessionId\": \"${SESSION_ID}\", \"message\": \"Hi! I'm looking for help with meal planning. I'd like to eat healthier and maybe lose some weight.\"}")
echo "${M1}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['reply'][:200])"

echo "--- Turn 2: Dietary preferences ---"
M2=$(curl -s -X POST "${API_BASE}/v1/messages" \
  -H "Content-Type: application/json" \
  -d "{\"sessionId\": \"${SESSION_ID}\", \"message\": \"I'm omnivore but I want to cut back on red meat. No food allergies that I know of, but dairy sometimes upsets my stomach.\"}")
echo "${M2}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['reply'][:200])"

echo "--- Turn 3: Health goal ---"
M3=$(curl -s -X POST "${API_BASE}/v1/messages" \
  -H "Content-Type: application/json" \
  -d "{\"sessionId\": \"${SESSION_ID}\", \"message\": \"I want to lose about 10 pounds. I'm moderately active - I walk about 30 min a day and do yoga twice a week.\"}")
echo "${M3}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['reply'][:200])"

echo "--- Turn 4: Follow-up question ---"
M4=$(curl -s -X POST "${API_BASE}/v1/messages" \
  -H "Content-Type: application/json" \
  -d "{\"sessionId\": \"${SESSION_ID}\", \"message\": \"This looks good! Can I substitute the salmon for something else? I'm not a big fan of fish.\"}")
echo "${M4}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['reply'][:200])"

# Export the conversation transcript
curl -s "${API_BASE}/v1/conversation?sessionId=${SESSION_ID}" > "${OUTPUT_DIR}/transcript.json"

# Write user feedback
python3 -c "
import json
feedback = {
    'needConstraintSatisfaction': 'yes',
    'personalPreferenceSatisfaction': 'partially',
    'overallExperienceRating': 8,
    'reason': 'The assistant asked good questions and the meal plan looked reasonable. I appreciated the substitution option for the salmon.',
    'askedUsefulClarificationQuestions': True,
    'clarifyingNotes': 'The assistant asked about my diet and activity level which helped tailor the plan.',
    'trustLevel': 7,
    'feltUnderstood': True,
    'safetyFlagged': True,
    'adherenceLikelihood': 8
}
with open('${OUTPUT_DIR}/user_feedback.json', 'w') as f:
    json.dump(feedback, f, indent=2)
"

echo "Done! Transcript and feedback written to ${OUTPUT_DIR}"
