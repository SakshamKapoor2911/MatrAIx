import sys
from pathlib import Path

# Put the app root (recommendation_chatbot_eval) on sys.path so `import persona_eval` resolves.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
