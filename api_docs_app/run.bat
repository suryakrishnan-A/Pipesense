@echo off
echo Starting PipeSense and DrainPilot Swagger UI Application on Port 5002...
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py
) else (
    python app.py
)
pause
