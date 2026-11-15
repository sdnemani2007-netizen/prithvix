import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv(Path(__file__).resolve().parent / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("WARNING: Gemini API key is missing!")
else:
    print("Gemini API key loaded successfully.")
# Add backend directory to sys.path so 'app' can be imported
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import uvicorn
from app.main import app

if __name__ == "__main__":
    print("=" * 60)
    print(" Starting PrithviX Backend Server on http://127.0.0.1:8000 ")
    print(" Interactive API Docs: http://127.0.0.1:8000/docs ")
    print("=" * 60)
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)
