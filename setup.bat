@echo off
REM Setup Script for Fake Review Detector (Windows)
REM This script helps with initial setup

setlocal enabledelayedexpansion

echo.
echo ========================================================
echo  FAKE REVIEW DETECTOR - WINDOWS SETUP
echo ========================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org
    pause
    exit /b 1
)

echo [1/5] Creating virtual environment...
if not exist ".venv" (
    python -m venv .venv
    echo ✓ Virtual environment created
) else (
    echo ✓ Virtual environment already exists
)

echo.
echo [2/5] Activating virtual environment...
call .venv\Scripts\activate.bat
echo ✓ Virtual environment activated

echo.
echo [3/5] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo ✓ Dependencies installed

echo.
echo [4/5] Creating .env file...
if not exist ".env" (
    copy .env.template .env
    echo ✓ .env file created
    echo   NOTE: Update .env with your MySQL credentials
) else (
    echo ✓ .env file already exists
)

echo.
echo [5/5] Downloading NLP data...
python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True); nltk.download('wordnet', quiet=True)"
echo ✓ NLP data downloaded

echo.
echo ========================================================
echo  SETUP COMPLETE!
echo ========================================================
echo.
echo Next steps:
echo 1. Edit .env with your MySQL credentials
echo 2. Ensure MySQL is running
echo 3. Run: python app.py
echo 4. Open: http://localhost:5000
echo.
pause
