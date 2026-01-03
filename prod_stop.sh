#!/bin/bash
# Production stop script for Anti-Oedipus application
# Usage: ./prod_stop.sh

set -e  # Exit on error

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

PID_FILE="${PID_FILE:-gunicorn.pid}"

if [ ! -f "$PID_FILE" ]; then
    echo "ERROR: PID file not found: $PID_FILE"
    echo "The application may not be running in daemon mode."
    exit 1
fi

PID=$(cat "$PID_FILE")

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "WARNING: Process $PID is not running. Removing stale PID file."
    rm -f "$PID_FILE"
    exit 1
fi

echo "Stopping Gunicorn process (PID: $PID)..."
kill "$PID"

# Wait for process to stop
for i in {1..10}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "Process stopped successfully."
        rm -f "$PID_FILE"
        exit 0
    fi
    sleep 1
done

# If still running, force kill
if ps -p "$PID" > /dev/null 2>&1; then
    echo "Process did not stop gracefully. Force killing..."
    kill -9 "$PID"
    rm -f "$PID_FILE"
    echo "Process force killed."
fi

