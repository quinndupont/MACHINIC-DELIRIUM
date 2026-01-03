#!/bin/bash
# Production start script for Anti-Oedipus application
# Usage: ./prod_start.sh

set -e  # Exit on error

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found. Please create it first:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    echo "ERROR: Flask is not installed. Please run: pip install -r requirements.txt"
    exit 1
fi

# Set Flask environment variables
export FLASK_APP=app.py
export FLASK_ENV=production

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found. Make sure environment variables are set."
fi

# Start Flask application
echo "Starting Flask application in production mode..."
echo "Host: 0.0.0.0"
echo "Port: 5001"
echo "Press Ctrl+C to stop"
echo ""

python -m flask run --host=0.0.0.0 --port=5001

