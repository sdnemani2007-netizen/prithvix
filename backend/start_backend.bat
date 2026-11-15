@echo off
cd /d "%~dp0"
echo ===================================================
echo Starting PrithviX Backend Server...
echo ===================================================
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    python main.py
)
pause
