#!/bin/bash

# Setup Script for Fake Review Detector (Mac/Linux)
# This script helps with initial setup

echo ""
echo "========================================================"
echo "  FAKE REVIEW DETECTOR - MAC/LINUX SETUP"
echo "========================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8+ from https://www.python.org"
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✓ Python $python_version found"

echo ""
echo "[1/5] Creating virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

echo ""
echo "[2/5] Activating virtual environment..."
source .venv/bin/activate
echo "✓ Virtual environment activated"

echo ""
echo "[3/5] Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi
echo "✓ Dependencies installed"

echo ""
echo "[4/5] Creating .env file..."
if [ ! -f ".env" ]; then
    cp .env.template .env
    echo "✓ .env file created"
    echo "  NOTE: Update .env with your MySQL credentials"
else
    echo "✓ .env file already exists"
fi

echo ""
echo "[5/5] Downloading NLP data..."
python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True); nltk.download('wordnet', quiet=True)"
echo "✓ NLP data downloaded"

echo ""
echo "========================================================"
echo "  SETUP COMPLETE!"
echo "========================================================"
echo ""
echo "Next steps:"
echo "1. Edit .env with your MySQL credentials"
echo "2. Ensure MySQL is running"
echo "3. Train models (optional): python train_models.py"
echo "4. Run: python app.py"
echo "5. Open: http://localhost:5000"
echo ""
