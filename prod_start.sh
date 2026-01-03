#!/bin/bash
# Production start script for Anti-Oedipus application
# Usage: ./prod_start.sh [--daemon]
#   --daemon: Run in background mode

set -e  # Exit on error

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Configuration
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-80}"
WORKERS="${WORKERS:-4}"
WORKER_CLASS="${WORKER_CLASS:-sync}"
TIMEOUT="${TIMEOUT:-120}"
LOG_LEVEL="${LOG_LEVEL:-info}"
ACCESS_LOG="${ACCESS_LOG:-logs/access.log}"
ERROR_LOG="${ERROR_LOG:-logs/error.log}"
PID_FILE="${PID_FILE:-gunicorn.pid}"

# Parse command line arguments
DAEMON_MODE=false
if [ "$1" = "--daemon" ]; then
    DAEMON_MODE=true
fi

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

# Check if Gunicorn is installed
if ! python -c "import gunicorn" 2>/dev/null; then
    echo "ERROR: Gunicorn is not installed. Installing now..."
    pip install gunicorn
    if ! python -c "import gunicorn" 2>/dev/null; then
        echo "ERROR: Failed to install Gunicorn. Please run: pip install gunicorn"
        exit 1
    fi
fi

# Check if Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    echo "ERROR: Flask is not installed. Please run: pip install -r requirements.txt"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found. Make sure environment variables are set."
fi

# Check if running on privileged port (requires root)
if [ "$PORT" -lt 1024 ] && [ "$EUID" -ne 0 ]; then
    echo "WARNING: Port $PORT requires root privileges."
    echo "Either run with sudo or set PORT to a higher port (e.g., PORT=8000 ./prod_start.sh)"
    echo ""
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Set production environment variables
export FLASK_APP=app.py
export FLASK_ENV=production

# Build Gunicorn command
GUNICORN_CMD="gunicorn"
GUNICORN_ARGS=(
    --bind "${HOST}:${PORT}"
    --workers "${WORKERS}"
    --worker-class "${WORKER_CLASS}"
    --timeout "${TIMEOUT}"
    --log-level "${LOG_LEVEL}"
    --access-logfile "${ACCESS_LOG}"
    --error-logfile "${ERROR_LOG}"
    --capture-output
    --enable-stdio-inheritance
    --preload
    "app:app"
)

# Add daemon mode if requested
if [ "$DAEMON_MODE" = true ]; then
    GUNICORN_ARGS+=(
        --daemon
        --pid "${PID_FILE}"
    )
    echo "Starting Gunicorn in daemon mode..."
    echo "PID file: ${PID_FILE}"
    echo "Logs: ${ACCESS_LOG} and ${ERROR_LOG}"
else
    echo "Starting Gunicorn in foreground mode..."
    echo "Press Ctrl+C to stop"
fi

echo "Configuration:"
echo "  Host: ${HOST}"
echo "  Port: ${PORT}"
echo "  Workers: ${WORKERS}"
echo "  Worker Class: ${WORKER_CLASS}"
echo "  Timeout: ${TIMEOUT}s"
echo "  Log Level: ${LOG_LEVEL}"
echo ""

# Start Gunicorn
exec "${GUNICORN_CMD}" "${GUNICORN_ARGS[@]}"

