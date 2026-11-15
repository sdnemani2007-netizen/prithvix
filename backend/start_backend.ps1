# PrithviX Backend Starter
Set-Location -Path $PSScriptRoot
Write-Host "===================================================" -ForegroundColor Green
Write-Host " Starting PrithviX Backend Server... " -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green

if (Test-Path ".\.venv\Scripts\python.exe") {
    & ".\.venv\Scripts\python.exe" main.py
} else {
    python main.py
}
