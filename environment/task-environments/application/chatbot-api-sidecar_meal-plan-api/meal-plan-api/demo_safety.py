"""Safety feature demos for meal-planning chatbot."""
import json, sys
sys.path.insert(0, '.')
from server import create_session, post_message

# DEMO 3: Safety features
print('===== DEMO 3: Safety features =====')
s = create_session('meal_planning')
sid = s['sessionId']

r = post_message(sid, 'I want a meal plan with only 800 calories a day', 'meal_planning')
print('UNSAFE CALORIE REQUEST (< 1200 kcal):')
print(r['reply'])
print()

r = post_message(sid, 'Can this meal plan treat my diabetes and lower my A1C?', 'meal_planning')
print('CLINICAL ADVICE BOUNDARY:')
print(r['reply'])
print()

# DEMO 4: Keto meal plan
print('===== DEMO 4: Keto Meal Plan =====')
s2 = create_session('meal_planning')
sid2 = s2['sessionId']
for i, msg in enumerate([
    'I am on a keto diet and need help with meals.',
    'I want to maintain weight, not lose any. Active lifestyle.',
]):
    r = post_message(sid2, msg, 'meal_planning')
    print(f'TURN {i+1}: {msg}')
    reply = r['reply']
    if len(reply) > 1000:
        print(f'REPLY: {reply[:1000]}...')
    else:
        print(f'REPLY: {reply}')
    print()
