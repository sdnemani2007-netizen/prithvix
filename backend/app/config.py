
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Base directory for the backend
BASE_DIR = Path(__file__).resolve().parent.parent

# Load backend/.env before reading environment variables
load_dotenv(BASE_DIR / ".env", override=False)

# Database configuration
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'prithvix.db'}"
)

# Google Earth Engine configuration
EE_PROJECT = os.environ.get("EE_PROJECT", "prithvix-514718")
EE_SERVICE_ACCOUNT_EMAIL = os.environ.get("EE_SERVICE_ACCOUNT_EMAIL", "")
EE_PRIVATE_KEY_PATH = os.environ.get("EE_PRIVATE_KEY_PATH", "")

# Gemini AI configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

if GEMINI_API_KEY:
    print("Gemini API key detected successfully.")
else:
    print("WARNING: GEMINI_API_KEY is missing.")

# CORS origins allow-list
DEFAULT_CORS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

custom_cors = os.environ.get("PRITHVIX_CORS_ORIGINS", "")

if custom_cors:
    CORS_ORIGINS = [
        x.strip() for x in custom_cors.split(",") if x.strip()
    ]
else:
    CORS_ORIGINS = DEFAULT_CORS

# Data caching TTL (hours)
CACHE_TTL_HOURS = int(
    os.environ.get("PRITHVIX_CACHE_TTL_HOURS", "24")
)
