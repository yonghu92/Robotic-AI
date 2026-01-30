#!/bin/bash
# Start the Piper Robot Web Controller

echo "========================================"
echo "  Piper Robot Web Controller"
echo "========================================"

# Install dependencies if needed
echo "[..] Checking dependencies..."
pip install flask flask-socketio opencv-python --quiet 2>/dev/null

# Change to script directory
cd "$(dirname "$0")"

# Start the web server
echo "[OK] Starting web server..."
python3 web_controller.py
