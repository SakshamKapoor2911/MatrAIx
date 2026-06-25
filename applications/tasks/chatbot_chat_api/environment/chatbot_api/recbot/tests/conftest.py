import sys
from pathlib import Path

# Put the chatbot API root on sys.path so `import recbot` works.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
