@echo off
setlocal

echo ========================================================
echo        Antigravity Web Dashboard Launcher
echo ========================================================

:: Check if python is in PATH
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not found in PATH. Please install Python.
    pause
    exit /b
)

:: Check if venv exists
if not exist venv (
    echo [1/3] Creating virtual environment...
    python -m venv venv
)

:: Activate venv
call venv\Scripts\activate.bat

:: Install requirements
echo [2/3] Checking requirements...
if exist requirements.txt (
    pip install -r requirements.txt -q
) else (
    echo requirements.txt not found. Skipping dependency installation.
)

:: Run the app
echo [3/3] Starting the Web Dashboard...
echo.
echo The dashboard will be available at http://127.0.0.1:5000
echo Press Ctrl+C to stop the server.
echo.

python src\web\app.py

pause
