"""
Configuration and environment settings for ATS automation.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Paths
BASE_DIR = Path(__file__).parent.parent
BACKEND_DIR = BASE_DIR.parent / "backend"

# Load .env from multiple locations (automation_script/.env and backend/.env)
load_dotenv(BASE_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")
DATA_DIR = BASE_DIR / "data"
PROFILES_DIR = DATA_DIR / "sample_profiles"
RESUMES_DIR = DATA_DIR / "resumes"
COVER_LETTERS_DIR = DATA_DIR / "cover_letters"

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Browser settings
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
SLOW_MO = int(os.getenv("SLOW_MO", "100"))  # Milliseconds between actions

# Screenshots
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)

# Timeouts
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "15000"))  # 15 seconds
NAVIGATION_TIMEOUT = int(os.getenv("NAVIGATION_TIMEOUT", "30000"))  # 30 seconds
