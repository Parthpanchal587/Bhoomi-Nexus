import sys
import os

# Add backend directory to sys.path so app modules are resolved correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, "..", "Bhoomi-Nexus", "backend")
if os.path.exists(backend_dir):
    sys.path.insert(0, backend_dir)

from app.main import app
