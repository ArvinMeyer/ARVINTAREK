@echo off
REM Quick Start Script for Email Extraction System
REM Windows PowerShell/CMD

echo ========================================
echo Email Extraction System - Quick Start
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo [SETUP] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment exists
)

echo.

REM Activate virtual environment
echo [SETUP] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)

echo [OK] Virtual environment activated
echo.

REM Check if dependencies are installed
echo [SETUP] Checking dependencies...
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [SETUP] Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed
) else (
    echo [OK] Dependencies already installed
)

echo.

REM Check if .env exists
if not exist ".env" (
    echo [SETUP] Creating .env file...
    copy .env.example .env >nul
    echo [OK] .env file created
    echo [INFO] Please edit .env file with your settings
) else (
    echo [OK] .env file exists
)

echo.

REM Check if database exists
if not exist "data\emails.db" (
    echo [SETUP] Initializing database...
    python main.py init-db
    if errorlevel 1 (
        echo [ERROR] Failed to initialize database
        pause
        exit /b 1
    )
    echo [OK] Database initialized
) else (
    echo [OK] Database exists
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Starting dashboard...
echo Dashboard will be available at: http://127.0.0.1:5000
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the dashboard
python main.py dashboard

pause
