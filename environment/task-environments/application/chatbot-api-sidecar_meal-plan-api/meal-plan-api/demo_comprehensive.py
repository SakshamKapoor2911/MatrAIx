"""Comprehensive demo of the meal-planning nutrition chatbot."""
import json, sys
sys.path.insert(0, '.')
from server import create_session, post_message, get_conversation

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║  MATRAIX  │  MEAL PLANNING & NUTRITION CHATBOT             ║
║  Branch: codex/meal-planning-nutrition-chatbot              ║
║  Type 2 Chatbot · System-prompt simulated sidecar           ║
╚══════════════════════════════════════════════════════════════╝
"""

print(BANNER)

# ======================================================================
# DEMO 1: Weight loss (omnivore) — routine balanced plan
# ======================================================================
print("=" * 60)
print("DEMO 1: Routine Balanced Plan (Weight Loss)")
print("=" * 60)
s = create_session('meal_planning')
sid = s['sessionId']
msgs = [
    "Hi! I need help planning meals. I want to eat healthier.",
    "I'm omnivore but want to cut red meat. Dairy sometimes upsets my stomach.",
    "I want to lose about 10 lbs. I walk 30 min daily and do yoga twice a week.",
    "This looks good! Can I substitute the salmon for something else? I don't like fish.",
]
for i, msg in enumerate(msgs):
    r = post_message(sid, msg, 'meal_planning')
    print(f"\n--- Turn {i+1} ---")
    print(f"  You: {msg}")
    reply = r['reply']
    if len(reply) > 900:
        print(f"  Bot: {reply[:900]}...")
    else:
        print(f"  Bot: {reply}")

# ======================================================================
# DEMO 2: Vegan high-protein (muscle gain)
# ======================================================================
print("\n\n" + "=" * 60)
print("DEMO 2: Vegan High-Protein Plan (Muscle Gain)")
print("=" * 60)
s2 = create_session('meal_planning')
sid2 = s2['sessionId']
msgs2 = [
    "I recently went vegan and need high-protein meals.",
    "I want to build muscle. No food allergies.",
    "I lift weights 4x a week, weigh 75kg. Goal is muscle gain.",
]
for i, msg in enumerate(msgs2):
    r = post_message(sid2, msg, 'meal_planning')
    print(f"\n--- Turn {i+1} ---")
    print(f"  You: {msg}")
    reply = r['reply']
    if len(reply) > 900:
        print(f"  Bot: {reply[:900]}...")
    else:
        print(f"  Bot: {reply}")

# ======================================================================
# DEMO 3: Safety features
# ======================================================================
print("\n\n" + "=" * 60)
print("DEMO 3: Safety Features")
print("=" * 60)
s3 = create_session('meal_planning')
sid3 = s3['sessionId']
r = post_message(sid3, "I want a meal plan with only 800 calories a day", 'meal_planning')
print(f"\n  You: I want a meal plan with only 800 calories a day")
print(f"  Bot: {r['reply']}")

# ======================================================================
# DEMO 4: Keto meal plan
# ======================================================================
print("\n\n" + "=" * 60)
print("DEMO 4: Keto Meal Plan")
print("=" * 60)
s4 = create_session('meal_planning')
sid4 = s4['sessionId']
msgs4 = [
    "I'm on a keto diet and need meal ideas please.",
    "I want to maintain weight, not lose. I am active.",
    "I run 3x a week and do HIIT. Goal is to maintain with keto.",
]
for i, msg in enumerate(msgs4):
    r = post_message(sid4, msg, 'meal_planning')
    print(f"\n--- Turn {i+1} ---")
    print(f"  You: {msg}")
    reply = r['reply']
    if len(reply) > 900:
        print(f"  Bot: {reply[:900]}...")
    else:
        print(f"  Bot: {reply}")

print("\n\n✅ All demos completed successfully.")
print("Task files:")
print("  └─ application/tasks/meal-planning-nutrition_chatbot/")
print("     ├── task.toml")
print("     ├── instruction.md")
print("     ├── input/ (chatbot.yaml, context.md, protocol.md, self_report_schema.yaml)")
print("     ├── tests/test_state.py (verifier)")
print("     └── solution/solve.sh")
print("  └─ environment/task-environments/application/meal-planning-nutrition_chatbot/")
print("     ├── docker-compose.yaml")
print("     ├── Dockerfile")
print("     └── meal-plan-api/")
print("        ├── server.py (FastAPI-style HTTP server)")
print("        ├── nutrition_data.py (50 food items, 5 templates, safety rules)")
print("        └── requirements.txt")
