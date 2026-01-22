#!/bin/bash
# Quick Start Script for Email Extraction System
# Linux/macOS

set -e

echo "========================================"
echo "Email Extraction System - Quick Start"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3.10 &> /dev/null; then
    echo "[ERROR] Python 3.10+ is not installed"
    echo "Please install Python 3.10 or higher"
    exit 1
fi

echo "[OK] Python found: $(python3.10 --version)"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "[SETUP] Creating virtual environment..."
    python3.10 -m venv venv
    echo "[OK] Virtual environment created"
else
    echo "[OK] Virtual environment exists"
fi

echo ""

# Activate virtual environment
echo "[SETUP] Activating virtual environment..."
source venv/bin/activate

echo "[OK] Virtual environment activated"
echo ""

# Check if dependencies are installed
echo "[SETUP] Checking dependencies..."
if ! python -c "import flask" &> /dev/null; then
    echo "[SETUP] Installing dependencies..."
    pip install -r requirements.txt
    echo "[OK] Dependencies installed"
else
    echo "[OK] Dependencies already installed"
fi

echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "[SETUP] Creating .env file..."
    cp .env.example .env
    echo "[OK] .env file created"
    echo "[INFO] Please edit .env file with your settings"
else
    echo "[OK] .env file exists"
fi

echo ""

# Check if database exists
if [ ! -f "data/emails.db" ]; then
    echo "[SETUP] Initializing database..."
    python main.py init-db
    echo "[OK] Database initialized"
else
    echo "[OK] Database exists"
fi

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Starting dashboard..."
echo "Dashboard will be available at: http://127.0.0.1:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the dashboard
python main.py dashboard
