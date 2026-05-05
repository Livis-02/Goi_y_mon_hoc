@echo off
cd /d "%~dp0"

echo Killing any process on port 8000...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr LISTENING ^| findstr ":8000"') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo Starting backend server...
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
