@echo off
echo ===================================================
echo  Starting PrithviX Agricultural Intelligence Platform
echo ===================================================
echo.
echo 1. Launching Backend (FastAPI on http://127.0.0.1:8000)...
start "PrithviX Backend" cmd /k "cd /d "%~dp0backend" && if exist ".venv\Scripts\python.exe" (".venv\Scripts\python.exe" main.py) else (python main.py)"

echo 2. Launching Frontend (Vite on http://localhost:5173)...
start "PrithviX Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo Both servers started!
echo Frontend: http://localhost:5173
echo Backend API & Swagger Docs: http://localhost:8000/docs
echo.
pause
