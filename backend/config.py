import os
from pathlib import Path

# Base directory of the project (one level up from backend/)
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

# Centralized Upload Directory
UPLOAD_DIR = PROJECT_ROOT / "uploads"

# Ensure directory exists
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

print(f"[Config] Backend Dir: {BACKEND_DIR}")
print(f"[Config] Project Root: {PROJECT_ROOT}")
print(f"[Config] Upload Dir: {UPLOAD_DIR}")
