import sys
import os

# Add backend directory to sys.path so app modules are resolved correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))

possible_paths = [
    os.path.join(root_dir, "Bhoomi-Nexus", "backend"),
    os.path.join(current_dir, "..", "Bhoomi-Nexus", "backend"),
    os.path.join(root_dir, "backend"),
    os.path.abspath("Bhoomi-Nexus/backend"),
    os.path.abspath("backend"),
]

for p in possible_paths:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

from app.main import app

